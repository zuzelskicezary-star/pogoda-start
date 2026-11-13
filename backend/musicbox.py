"""Music Box: Polish online radio, built from generic blocks (ADR 0001).

Two screens: the station grid (no params) and the player (``station=<uuid>``).
The TV computes nothing: previous/next station, CH+/CH- and the list on the
right are ``open_screen`` actions whose targets are worked out here.
"""

import colorsys
import hashlib
import threading

from backend.screens import (
    back, button, column, grid, image, item_list, open_screen, row, screen, text, tile, toggle_pause, volume,
)

APP_ID = "musicbox"
GRID_COLUMNS = 5
EMPTY_TEXT = "Brak dostępnych stacji, spróbuj później"
STREAM_ERROR_TEXT = "Ta stacja teraz nie nadaje. Wybierz inną."
VOLUME_STEP = 10


class StationNotFound(LookupError):
    pass


def fallback_color(name):
    """A stable colour for a station without a (working) logo."""
    digest = hashlib.md5(name.encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") / 65536
    r, g, b = colorsys.hls_to_rgb(hue, 0.38, 0.55)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def station_image(station):
    return image(station["logo"], fallback_color(station["name"]), station["name"])


class MusicBox:
    def __init__(self, stations):
        self.stations = stations
        # Every station seen so far, by uuid: a station that drops out of the
        # list on a refresh still has a player, so it keeps playing.
        self._known = {}
        self._lock = threading.Lock()

    def screen(self, device, app, params):
        stations = self._current()
        if params.get("station"):
            return self.player(device, stations, params["station"])
        return self.station_grid(device, app, stations)

    def _current(self):
        stations = self.stations.current()
        with self._lock:
            for s in stations:
                self._known[s["id"]] = s
        return stations

    def _known_station(self, uuid):
        with self._lock:
            if uuid not in self._known:
                raise StationNotFound(uuid)
            return self._known[uuid]

    def station_grid(self, device, app, stations):
        if not stations:
            return screen(APP_ID, column(text(app["name"], style="title"), text(EMPTY_TEXT)))
        tiles = [
            tile("station-" + s["id"], s["name"], station_image(s),
                 open_screen(device["id"], APP_ID, station=s["id"]))
            for s in stations
        ]
        return screen(
            APP_ID,
            column(text(app["name"], style="title"), grid(GRID_COLUMNS, *tiles)),
            focus=tiles[0]["id"],
        )

    def player(self, device, stations, uuid):
        playing = self._known_station(uuid)

        def switch_to(station):
            return open_screen(device["id"], APP_ID, replace=True, station=station["id"])

        previous, next_station = neighbours(stations, playing)
        playback = row(
            button("prev", "⏮ Poprzednia", switch_to(previous)),
            button("playpause", "⏯ Play / pauza", toggle_pause()),
            button("next", "Następna ⏭", switch_to(next_station)),
        )
        sound_and_exit = row(
            button("volume-down", "🔉 −", volume(-VOLUME_STEP)),
            button("volume-up", "🔊 +", volume(VOLUME_STEP)),
            button("back", "↩ Wróć do stacji", back()),
        )
        now_playing = column(
            station_image(playing),
            text(playing["name"], style="title"),
            playback,
            sound_and_exit,
            flex=3,
        )
        others = column(
            text("Pozostałe stacje", style="hint"),
            item_list(*[
                tile("station-" + s["id"], s["name"], station_image(s), switch_to(s))
                for s in stations if s["id"] != playing["id"]
            ]),
            flex=2,
        )
        return screen(
            APP_ID,
            row(now_playing, others),
            focus="playpause",
            keys={"chup": switch_to(next_station), "chdown": switch_to(previous)},
            stream={"url": playing["stream"], "error": STREAM_ERROR_TEXT},
        )


def neighbours(stations, playing):
    """Previous and next station in the list, wrapping around at the ends.

    A station no longer on the list sits before its start: next is the first
    station, previous the last. With no list, both are the station itself.
    """
    if not stations:
        return playing, playing
    ids = [s["id"] for s in stations]
    if playing["id"] not in ids:
        return stations[-1], stations[0]
    i = ids.index(playing["id"])
    return stations[i - 1], stations[(i + 1) % len(stations)]
