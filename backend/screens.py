"""App screens: what the TV shows after opening an app (ADR 0001).

The TV knows no app. It draws a screen built from a closed vocabulary of
blocks and runs actions from a closed vocabulary; the backend decides the rest.

Screen::

    {"app_id": str, "refresh": seconds, "focus": block id or None,
     "keys": {"chup": action, "chdown": action}, "root": block}

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

``focus`` may name any focusable block (button, tile).

Actions:

- ``{"type": "open_screen", "path": "/api/devices/<id>/apps/<app>/screen?..."}``
- ``{"type": "back"}``
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


def open_screen(device_id, app_id, **params):
    path = screen_path(device_id, app_id)
    if params:
        path += "?" + urlencode(params)
    return {"type": "open_screen", "path": path}


def back():
    return {"type": "back"}


def screen_path(device_id, app_id):
    return "/api/devices/%s/apps/%s/screen" % (quote(device_id, safe=""), quote(app_id, safe=""))


def screen(app_id, root, focus=None, keys=None, refresh=DEFAULT_REFRESH_S):
    return {"app_id": app_id, "refresh": refresh, "focus": focus, "keys": keys or {}, "root": root}


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
    for app in apps:
        if app["id"] == app_id:
            return screens.get(app_id, default_screen)(device, app, params)
    raise AppNotFound(app_id)
