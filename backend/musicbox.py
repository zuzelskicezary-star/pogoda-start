"""Music Box: Polish online radio, built from generic blocks (ADR 0001)."""

import colorsys
import hashlib

from backend.screens import column, grid, image, open_screen, screen, text, tile

APP_ID = "musicbox"
GRID_COLUMNS = 5
EMPTY_TEXT = "Brak dostępnych stacji, spróbuj później"


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

    def screen(self, device, app, params):
        return self.station_grid(device, app)

    def station_grid(self, device, app):
        stations = self.stations.current()
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

