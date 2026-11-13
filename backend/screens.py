"""App screens: what the TV shows after opening an app (ADR 0001).

The TV knows no app. It draws a screen built from a closed vocabulary of
blocks and runs actions from a closed vocabulary; the backend decides the rest.

Screen::

    {"app_id": str, "refresh": seconds, "focus": block id or None,
     "keys": {"chup": action, "chdown": action}, "root": block,
     "stream": {"url": str, "error": str}}   # optional

``stream`` is what should be playing on this screen: the TV starts it unless
it already plays that url (so a refresh never interrupts the sound) and shows
``error`` when the audio fails. A screen without ``stream`` leaves audio as is.

``focus`` names the button focused on entry; ``keys`` maps CH+/CH- to actions
(an unmapped key keeps its TV meaning); the TV fetches the screen again every
``refresh`` seconds. Unknown blocks are skipped and unknown actions ignored.

Blocks (any block may carry ``flex``: its share of the parent layout; without
it the block takes its natural size):

- ``{"type": "row" | "column", "children": [block, ...]}``
- ``{"type": "text", "text": str, "style": "title" | "body" | "hint"}``
- ``{"type": "button", "id": str, "label": str, "action": action}``
- ``{"type": "image", "url": str | None, "color": "#rrggbb", "text": str}``:
  the picture, or ``text`` on ``color`` when there is no url or it fails to load
- ``{"type": "tile", "id": str, "label": str, "image": image, "action": action}``
- ``{"type": "grid", "columns": int, "children": [block, ...]}``
- ``{"type": "list", "children": [block, ...]}``: a scrolling column of
  focusable items (buttons or tiles)

``focus`` may name any focusable block (button, tile).

Actions:

- ``{"type": "open_screen", "path": "/api/devices/<id>/apps/<app>/screen?...",
  "replace": true}``: ``replace`` (optional) swaps the current screen instead of
  stacking the new one, so ``back`` skips it
- ``{"type": "back"}``
- ``{"type": "play", "url": str, "error": str}``: play a stream from its source
- ``{"type": "toggle_pause"}``
- ``{"type": "volume", "step": int}``: change the volume by ``step`` percent
- ``{"type": "post", "path": "/api/...", "body": object}``: send ``body`` to the
  backend, then refresh the current screen (keeping focus and sound)
"""

from urllib.parse import quote, urlencode

DEFAULT_REFRESH_S = 60


class AppNotFound(LookupError):
    pass


# --- vocabulary -------------------------------------------------------------

def column(*children, **extra):
    return dict(type="column", children=list(children), **extra)


def row(*children, **extra):
    return dict(type="row", children=list(children), **extra)


def text(value, style="body", **extra):
    return dict(type="text", text=value, style=style, **extra)


def button(block_id, label, action, **extra):
    return dict(type="button", id=block_id, label=label, action=action, **extra)


def image(url, color, fallback_text, **extra):
    return dict(type="image", url=url, color=color, text=fallback_text, **extra)


def tile(block_id, label, picture, action, **extra):
    return dict(type="tile", id=block_id, label=label, image=picture, action=action, **extra)


def grid(columns, *children, **extra):
    return dict(type="grid", columns=columns, children=list(children), **extra)


def item_list(*children, **extra):
    return dict(type="list", children=list(children), **extra)


def open_screen(device_id, app_id, replace=False, **params):
    path = screen_path(device_id, app_id)
    if params:
        path += "?" + urlencode(params)
    action = {"type": "open_screen", "path": path}
    if replace:
        action["replace"] = True
    return action


def back():
    return {"type": "back"}


def play(url, error):
    return {"type": "play", "url": url, "error": error}


def toggle_pause():
    return {"type": "toggle_pause"}


def volume(step):
    return {"type": "volume", "step": step}


def post(path, body):
    return {"type": "post", "path": path, "body": body}


def screen_path(device_id, app_id):
    return "/api/devices/%s/apps/%s/screen" % (quote(device_id, safe=""), quote(app_id, safe=""))


def screen(app_id, root, focus=None, keys=None, refresh=DEFAULT_REFRESH_S, stream=None):
    described = {"app_id": app_id, "refresh": refresh, "focus": focus, "keys": keys or {}, "root": root}
    if stream:
        described["stream"] = stream
    return described


# --- screens ----------------------------------------------------------------

def default_screen(device, app, params):
    """What every app showed before the backend described screens: its name."""
    return screen(app["id"], column(
        text(app["name"], style="title"),
        text("BACK — powrót do menu", style="hint"),
    ))


def build_screen(device, apps, app_id, params, screens):
    """``apps`` is what the device sees in the catalog; others are not found.

    ``screens`` maps the id of an app with a screen of its own to its builder,
    ``builder(device, app, params)``; other apps get the default screen.
    """
    app = find_app(apps, app_id)
    return screens.get(app_id, default_screen)(device, app, params)


def find_app(apps, app_id):
    """The app among those the device sees in the catalog."""
    for app in apps:
        if app["id"] == app_id:
            return app
    raise AppNotFound(app_id)
