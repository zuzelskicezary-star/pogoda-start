/* Lumio TV client. Shipped in firmware; talks to the backend over JSON. */
(function () {
  "use strict";

  var CHECK_INTERVAL_MS = 5000;
  var DOWNLOAD_MS = 3000;
  var INSTALL_MS = 1500;
  var GRID_COLUMNS = 5;

  var params = new URLSearchParams(window.location.search);
  var deviceId = params.get("device") || "TV-001";

  var tv = {
    device: null,
    state: "menu",
    apps: [],
    focus: 0,
    channel: 1,
    updating: false,
    lastCheck: null,
    app: null, /* open app: { id, name, stack: [{ path, focusId }], screen, focusId, seq, timer } */
    stream: null, /* the stream being played: { url, error } */
    volume: 100 /* percent, kept for the session */
  };

  var audio = new Audio();
  var audioMessageTimer = null;

  var el = function (id) { return document.getElementById(id); };

  function api(method, path, body) {
    var options = { method: method, headers: {} };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(path, options).then(function (res) {
      el("offline").hidden = true;
      return res.json().then(function (data) {
        if (!res.ok) { throw new Error(data.error || ("HTTP " + res.status)); }
        return data;
      });
    }, function (err) {
      el("offline").hidden = false;
      throw err;
    });
  }

  function log(text, kind) {
    var item = document.createElement("li");
    var time = document.createElement("time");
    time.textContent = new Date().toLocaleTimeString("pl-PL");
    item.appendChild(time);
    item.appendChild(document.createTextNode(text));
    if (kind) { item.className = kind; }
    var list = el("log");
    list.insertBefore(item, list.firstChild);
    while (list.children.length > 200) { list.removeChild(list.lastChild); }
  }

  /* ---------- rendering ---------- */

  function renderStatus() {
    var d = tv.device;
    el("sb-device").textContent = d.id;
    el("sb-model").textContent = d.model_name + " (" + d.model + ")";
    el("sb-region").textContent = d.region;
    el("sb-firmware").textContent = d.firmware;
    el("downloads").textContent = d.downloads;
  }

  function renderClock() {
    if (!tv.device) { return; }
    var now = new Date(Date.now() + tv.device.utc_offset_min * 60000);
    var hh = String(now.getUTCHours()).padStart(2, "0");
    var mm = String(now.getUTCMinutes()).padStart(2, "0");
    el("sb-clock").textContent = hh + ":" + mm;
  }

  function renderGrid() {
    var grid = el("grid");
    grid.innerHTML = "";
    tv.apps.forEach(function (app, i) {
      var tile = document.createElement("div");
      tile.className = "tile" + (app.featured ? " featured" : "") + (i === tv.focus ? " focused" : "");
      tile.style.background = app.color;
      tile.innerHTML = "<span></span><small></small>";
      tile.firstChild.textContent = app.name;
      tile.lastChild.textContent = "v" + app.version;
      tile.addEventListener("click", function () { tv.focus = i; openApp(); });
      grid.appendChild(tile);
    });
  }

  function setState(state) {
    tv.state = state;
    el("screen").setAttribute("data-state", state);
    api("POST", "/api/devices/" + deviceId + "/report", { state: state }).catch(function () {});
  }

  /* ---------- app screens (ADR 0001) ----------
   * The backend describes every app screen with blocks and actions from a
   * closed vocabulary. Unknown blocks are skipped and unknown actions ignored,
   * so a newer backend never breaks this client.
   */

  function setView(view) {
    el("screen").setAttribute("data-view", view);
  }

  function div(className, text) {
    var node = document.createElement("div");
    node.className = className;
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  function appendChildren(node, children) {
    (children || []).forEach(function (child) {
      var c = renderBlock(child);
      if (!c) { return; }
      if (typeof child.flex === "number") { c.style.flex = child.flex + " 1 0"; }
      node.appendChild(c);
    });
  }

  /* Focusable blocks: OK (or a click) runs their action. */
  function makeFocusable(node, block) {
    node.classList.add("focusable");
    node.setAttribute("data-id", block.id);
    node.addEventListener("click", function () {
      if (!tv.app) { return; }
      tv.app.focusId = block.id;
      markFocus();
      runAction(block.action);
    });
    return node;
  }

  /* The picture, or its text on its colour when there is none or it fails. */
  function renderImage(block) {
    var node = div("blk-image");
    node.style.background = block.color || "#444";
    function showText() {
      node.innerHTML = "";
      node.appendChild(div("blk-image-text", block.text || ""));
    }
    if (block.url) {
      var img = document.createElement("img");
      img.alt = block.text || "";
      img.addEventListener("error", showText);
      img.src = block.url;
      node.appendChild(img);
    } else {
      showText();
    }
    return node;
  }

  function renderBlock(block) {
    var node;
    if (!block) { return null; }
    if (block.type === "row" || block.type === "column") {
      node = div("blk-" + block.type);
      appendChildren(node, block.children);
    } else if (block.type === "list") {
      node = div("blk-list");
      appendChildren(node, block.children);
    } else if (block.type === "grid") {
      node = div("blk-grid");
      node.style.gridTemplateColumns = "repeat(" + Math.max(1, block.columns || 1) + ", minmax(0, 1fr))";
      appendChildren(node, block.children);
    } else if (block.type === "text") {
      node = div("blk-text " + (block.style || "body"), block.text);
    } else if (block.type === "image") {
      node = renderImage(block);
    } else if (block.type === "button") {
      node = makeFocusable(div("blk-button", block.label), block);
    } else if (block.type === "tile") {
      node = makeFocusable(div("blk-tile"), block);
      if (block.image) { node.appendChild(renderImage(block.image)); }
      node.appendChild(div("blk-tile-label", block.label));
    } else {
      return null;
    }
    return node;
  }

  function focusables() {
    return Array.prototype.slice.call(el("appscreen").querySelectorAll(".focusable"));
  }

  function focusedNode() {
    var id = tv.app && tv.app.focusId;
    return focusables().filter(function (n) { return n.getAttribute("data-id") === id; })[0] || null;
  }

  function markFocus() {
    var current = focusedNode();
    focusables().forEach(function (n) { n.classList.toggle("focused", n === current); });
    if (current && current.scrollIntoView) { current.scrollIntoView({ block: "nearest" }); }
  }

  function renderAppScreen() {
    var root = el("appscreen");
    root.innerHTML = "";
    var node = tv.app.screen && renderBlock(tv.app.screen.root);
    if (node) { root.appendChild(node); }
    if (!focusedNode()) { tv.app.focusId = tv.app.screen ? tv.app.screen.focus : null; }
    markFocus();
  }

  function scheduleRefresh(seconds) {
    var app = tv.app;
    clearTimeout(app.timer);
    app.timer = setTimeout(function () {
      if (tv.app === app) { loadScreen(topEntry(), false); }
    }, Math.max(1, seconds || 60) * 1000);
  }

  function topEntry() {
    return tv.app.stack[tv.app.stack.length - 1];
  }

  /* Fetches and shows the screen of `entry`.
   * fresh: a newly entered screen (focus from its description, or the one
   * remembered when going back); otherwise a refresh that keeps focus.
   * commit: updates the navigation stack, only once the fetch succeeded,
   * so a failed fetch leaves both the screen and the stack as they were. */
  function loadScreen(entry, fresh, commit) {
    var app = tv.app;
    var seq = ++app.seq;
    clearTimeout(app.timer);
    api("GET", entry.path).then(function (screen) {
      if (tv.app !== app || app.seq !== seq) { return; }
      if (commit) { commit(); }
      app.screen = screen;
      if (fresh) { app.focusId = entry.focusId || screen.focus; }
      renderAppScreen();
      if (screen.stream) { playStream(screen.stream, fresh); }
      scheduleRefresh(screen.refresh);
    }, function (err) {
      if (tv.app !== app || app.seq !== seq) { return; }
      log("Nie można pobrać ekranu " + app.name + ": " + err.message, "warn");
      if (!app.screen) {
        app.screen = { root: { type: "text", style: "title", text: app.name }, focus: null, keys: {} };
        renderAppScreen();
      }
      scheduleRefresh(app.screen.refresh);
    });
  }

  /* replace: swap the current screen instead of stacking the new one. */
  function openScreen(path, replace) {
    var app = tv.app;
    var next = { path: path, focusId: null };
    loadScreen(next, true, function () {
      if (replace) {
        app.stack[app.stack.length - 1] = next;
      } else {
        app.stack[app.stack.length - 1].focusId = app.focusId;
        app.stack.push(next);
      }
    });
  }

  function goBack() {
    var app = tv.app;
    if (app.stack.length > 1) {
      loadScreen(app.stack[app.stack.length - 2], true, function () { app.stack.pop(); });
    } else {
      closeApp();
      setState("menu");
    }
  }

  function runAction(action) {
    if (!action || !tv.app) { return; }
    if (action.type === "open_screen" && action.path) {
      openScreen(action.path, action.replace === true);
    } else if (action.type === "back") {
      goBack();
    } else if (action.type === "play" && action.url) {
      playStream(action, true);
    } else if (action.type === "toggle_pause") {
      togglePause();
    } else if (action.type === "volume" && typeof action.step === "number") {
      changeVolume(action.step);
    } else if (action.type === "post" && action.path) {
      postAndRefresh(action.path, action.body);
    }
  }

  /* Send something to the backend, then show the screen as it is now. */
  function postAndRefresh(path, body) {
    var app = tv.app;
    api("POST", path, body || {}).then(function () {
      if (tv.app === app) { loadScreen(topEntry(), false); }
    }, function (err) {
      log("Nie udało się wysłać: " + err.message, "warn");
    });
  }

  /* ---------- audio: streams play straight from the broadcaster ---------- */

  function showAudioMessage(message, kind, ms) {
    var box = el("audio-msg");
    clearTimeout(audioMessageTimer);
    box.textContent = message;
    box.className = "audio-msg " + (kind || "");
    box.hidden = false;
    if (ms) { audioMessageTimer = setTimeout(hideAudioMessage, ms); }
  }

  function hideAudioMessage() {
    clearTimeout(audioMessageTimer);
    el("audio-msg").hidden = true;
  }

  function showStreamError() {
    if (tv.stream) { showAudioMessage(tv.stream.error || "Błąd odtwarzania", "error"); }
  }

  function startAudio() {
    audio.volume = tv.volume / 100;
    var playing = audio.play();
    if (playing && playing.catch) {
      playing.catch(function (err) {
        if (err.name === "AbortError") { return; }
        if (err.name === "NotAllowedError") {
          log("Przeglądarka wstrzymała autoodtwarzanie", "warn");
          showAudioMessage("Naciśnij OK na „Play / pauza”, aby słuchać", "");
          return;
        }
        showStreamError();
      });
    }
  }

  /* A new url starts playing. The same url keeps playing undisturbed, so a
   * screen refresh never interrupts the sound; entering a screen anew
   * (fresh) resumes it if it was paused. */
  function playStream(stream, fresh) {
    if (tv.stream && tv.stream.url === stream.url) {
      tv.stream.error = stream.error;
      if (fresh && audio.paused) { hideAudioMessage(); startAudio(); }
      return;
    }
    tv.stream = { url: stream.url, error: stream.error };
    hideAudioMessage();
    audio.src = stream.url;
    startAudio();
    log("Odtwarzanie: " + stream.url);
  }

  function stopAudio() {
    tv.stream = null;
    hideAudioMessage();
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }

  function togglePause() {
    if (!tv.stream) { return; }
    if (audio.paused) {
      hideAudioMessage();
      startAudio();
    } else {
      audio.pause();
      showAudioMessage("Pauza", "", 1500);
    }
  }

  function changeVolume(step) {
    tv.volume = Math.min(100, Math.max(0, Math.round(tv.volume + step)));
    audio.volume = tv.volume / 100;
    showAudioMessage("Głośność " + tv.volume + "%", "", 1500);
  }

  audio.addEventListener("error", function () {
    if (tv.stream && audio.getAttribute("src")) { showStreamError(); }
  });

  /* Arrows move focus to the nearest focusable block in that direction. */
  function moveFocus(key) {
    var nodes = focusables();
    if (!nodes.length) { return; }
    var current = focusedNode();
    if (!current) {
      tv.app.focusId = nodes[0].getAttribute("data-id");
      markFocus();
      return;
    }
    var from = current.getBoundingClientRect();
    var fx = from.left + from.width / 2, fy = from.top + from.height / 2;
    var best = null, bestScore = Infinity;
    nodes.forEach(function (n) {
      if (n === current) { return; }
      var r = n.getBoundingClientRect();
      var dx = r.left + r.width / 2 - fx, dy = r.top + r.height / 2 - fy;
      var main = { left: -dx, right: dx, up: -dy, down: dy }[key];
      var side = (key === "left" || key === "right") ? Math.abs(dy) : Math.abs(dx);
      if (!(main > 0)) { return; }
      var score = main + 2 * side;
      if (score < bestScore) { bestScore = score; best = n; }
    });
    if (best) {
      tv.app.focusId = best.getAttribute("data-id");
      markFocus();
    }
  }

  function openApp() {
    var app = tv.apps[tv.focus];
    if (!app) { return; }
    closeApp();
    tv.app = {
      id: app.id,
      name: app.name,
      stack: [{ path: "/api/devices/" + encodeURIComponent(deviceId) + "/apps/" + encodeURIComponent(app.id) + "/screen", focusId: null }],
      screen: null,
      focusId: null,
      seq: 0,
      timer: null
    };
    el("appscreen").innerHTML = "";
    setView("app");
    setState("watching");
    loadScreen(topEntry(), true);
  }

  function closeApp() {
    if (tv.app) { clearTimeout(tv.app.timer); }
    if (tv.stream) { stopAudio(); }
    tv.app = null;
    setView("channel");
  }

  /* ---------- remote control ---------- */

  function watchChannel() {
    closeApp();
    el("player-title").textContent = "Kanał " + tv.channel;
    setState("watching");
  }

  function press(key) {
    if (key === "power") {
      closeApp();
      setState(tv.state === "standby" ? "menu" : "standby");
      log(tv.state === "standby" ? "Tryb czuwania" : "Włączono");
      return;
    }
    if (tv.state === "standby") { return; }

    var keys = tv.app && tv.app.screen && tv.app.screen.keys;
    if (key === "back" && tv.app) {
      goBack();
    } else if (key === "home" || key === "back") {
      closeApp();
      setState("menu");
    } else if ((key === "chup" || key === "chdown") && keys && keys[key]) {
      runAction(keys[key]);
    } else if (key === "chup" || key === "chdown") {
      tv.channel = Math.max(1, tv.channel + (key === "chup" ? 1 : -1));
      watchChannel();
    } else if (tv.state === "menu") {
      var n = tv.apps.length;
      if (key === "left") { tv.focus = Math.max(0, tv.focus - 1); }
      if (key === "right") { tv.focus = Math.min(n - 1, tv.focus + 1); }
      if (key === "up") { tv.focus = Math.max(0, tv.focus - GRID_COLUMNS); }
      if (key === "down") { tv.focus = Math.min(n - 1, tv.focus + GRID_COLUMNS); }
      if (key === "ok") { openApp(); }
      renderGrid();
    } else if (tv.app) {
      if (key === "ok") {
        var node = focusedNode();
        if (node) { node.click(); }
      } else {
        moveFocus(key);
      }
    }
  }

  var KEYS = {
    ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
    Enter: "ok", Escape: "back", Backspace: "back", h: "home", p: "power",
    PageUp: "chup", PageDown: "chdown"
  };

  /* ---------- firmware updates ---------- */

  function checkForUpdate() {
    if (tv.updating || !tv.device) { return; }
    api("POST", "/api/ota/check", {
      device_id: deviceId,
      firmware: tv.device.firmware,
      state: tv.state,
      utc_offset_min: tv.device.utc_offset_min
    }).then(function (res) {
      if (res.update) {
        installUpdate(res.update);
      } else if (tv.lastCheck !== "none") {
        log("Brak aktualizacji (FW " + tv.device.firmware + ")");
      }
      tv.lastCheck = res.update ? "update" : "none";
    }).catch(function (err) {
      log("Błąd sprawdzania aktualizacji: " + err.message, "warn");
    });
  }

  function animateProgress(ms) {
    return new Promise(function (resolve) {
      var start = Date.now();
      var timer = setInterval(function () {
        var p = Math.min(1, (Date.now() - start) / ms);
        el("progress-bar").style.width = Math.round(p * 100) + "%";
        if (p >= 1) { clearInterval(timer); resolve(); }
      }, 100);
    });
  }

  function wait(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function installUpdate(update) {
    tv.updating = true;
    var mb = Math.round(update.size_bytes / 1048576);
    log("Dostępna aktualizacja " + update.build + " (" + mb + " MB)", "warn");
    el("banner").hidden = false;
    el("banner-title").textContent = "Pobieranie aktualizacji " + update.build;
    el("banner-notes").textContent = update.notes || "";
    el("progress-bar").style.width = "0";

    api("POST", "/api/ota/download", { device_id: deviceId, build: update.build })
      .then(function () { return animateProgress(DOWNLOAD_MS); })
      .then(function () {
        el("banner-title").textContent = "Instalowanie " + update.build + "…";
        return wait(INSTALL_MS);
      })
      .then(function () {
        return api("POST", "/api/devices/" + deviceId + "/report", {
          firmware: update.build,
          state: tv.state
        });
      })
      .then(function () {
        log("Zainstalowano " + update.build + ", restart", "ok");
        return refreshDevice();
      })
      .catch(function (err) {
        log("Aktualizacja nieudana: " + err.message, "warn");
      })
      .then(function () {
        el("banner").hidden = true;
        tv.updating = false;
        tv.lastCheck = null;
      });
  }

  /* ---------- boot ---------- */

  function refreshDevice() {
    return api("GET", "/api/devices/" + deviceId).then(function (device) {
      tv.device = device;
      renderStatus();
      renderClock();
      return api("GET", "/api/devices/" + deviceId + "/apps");
    }).then(function (res) {
      tv.apps = res.apps;
      tv.focus = Math.min(tv.focus, Math.max(0, tv.apps.length - 1));
      renderGrid();
    });
  }

  function renderDeviceLinks() {
    api("GET", "/api/devices").then(function (res) {
      var nav = el("devices");
      nav.innerHTML = "";
      res.devices.forEach(function (d) {
        var a = document.createElement("a");
        a.href = "?device=" + encodeURIComponent(d.id);
        a.textContent = d.id + " · " + d.model + " · " + d.region;
        if (d.id === deviceId) { a.className = "current"; }
        nav.appendChild(a);
      });
    }).catch(function () {});
  }

  function boot() {
    document.title = "Lumio TV · " + deviceId;
    document.querySelectorAll("[data-key]").forEach(function (button) {
      button.addEventListener("click", function () { press(button.getAttribute("data-key")); });
    });
    document.addEventListener("keydown", function (e) {
      if (KEYS[e.key]) { e.preventDefault(); press(KEYS[e.key]); }
    });

    refreshDevice().then(function () {
      log("Uruchomiono " + deviceId + ", FW " + tv.device.firmware);
      setState(tv.state);
      checkForUpdate();
      setInterval(checkForUpdate, CHECK_INTERVAL_MS);
      setInterval(renderClock, 10000);
    }).catch(function (err) {
      log("Nie można uruchomić " + deviceId + ": " + err.message, "warn");
    });
    renderDeviceLinks();
  }

  boot();
})();
