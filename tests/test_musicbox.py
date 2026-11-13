"""Music Box screens seen through the API, with a fake station source."""

import json
import re

from backend.api import Api
from backend.stations import StaticStations
from tests.support import ServerTestCase, StoreTestCase


def station(uuid, name, logo="https://logo.example/%s.png"):
    return {
        "id": uuid,
        "name": name,
        "logo": logo % uuid if logo and "%s" in logo else logo,
        "stream": "https://stream.example/%s" % uuid,
    }


STATIONS = [
    station("a1", "RMF FM"),
    station("b2", "Radio ZET", logo=None),
    station("c3", "Polskie Radio Trójka"),
]


def walk(block):
    yield block
    for child in block.get("children", []):
        yield from walk(child)
    if block.get("image"):
        yield from walk(block["image"])


def blocks(screen, kind):
    return [b for b in walk(screen["root"]) if b["type"] == kind]


class MusicBoxGridTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.stations = StaticStations(STATIONS)
        self.api = Api(self.store, stations=self.stations)

    def screen(self, device_id="TV-006", api=None):
        return (api or self.api).handle("GET", "/api/devices/%s/apps/musicbox/screen" % device_id)

    def test_grid_has_a_tile_per_station_in_source_order(self):
        status, screen = self.screen()
        self.assertEqual(status, 200)
        (grid,) = blocks(screen, "grid")
        self.assertIsInstance(grid["columns"], int)
        self.assertEqual([t["label"] for t in grid["children"]], ["RMF FM", "Radio ZET", "Polskie Radio Trójka"])
        self.assertTrue(all(t["type"] == "tile" for t in grid["children"]))

    def test_tile_shows_logo_with_fallback_colour_and_name(self):
        _, screen = self.screen()
        rmf, zet, _ = blocks(screen, "tile")
        self.assertEqual(rmf["image"], {
            "type": "image", "url": "https://logo.example/a1.png", "color": rmf["image"]["color"], "text": "RMF FM",
        })
        self.assertRegex(rmf["image"]["color"], r"^#[0-9a-f]{6}$")
        self.assertIsNone(zet["image"]["url"])
        self.assertEqual(zet["image"]["text"], "Radio ZET")

    def test_fallback_colour_depends_only_on_the_name(self):
        _, first = self.screen()
        renamed = [station("zz", "RMF FM", logo=None)]
        _, second = self.screen(api=Api(self.store, stations=StaticStations(renamed)))
        colours = [t["image"]["color"] for t in blocks(first, "tile")]
        self.assertEqual(blocks(second, "tile")[0]["image"]["color"], colours[0])
        self.assertEqual(len(set(colours)), 3)

    def test_tile_opens_the_player_of_its_station(self):
        _, screen = self.screen("TV-004")
        tile = blocks(screen, "tile")[0]
        self.assertEqual(tile["action"], {
            "type": "open_screen", "path": "/api/devices/TV-004/apps/musicbox/screen?station=a1",
        })

    def test_first_tile_has_focus_and_screen_refreshes_every_minute(self):
        _, screen = self.screen()
        tiles = blocks(screen, "tile")
        self.assertEqual(screen["focus"], tiles[0]["id"])
        self.assertEqual(len({t["id"] for t in tiles}), 3)
        self.assertEqual(screen["refresh"], 60)

    def test_same_stations_in_every_region(self):
        devices = self.store.fixture("devices")
        devices.append({"id": "TV-NA", "model": "LM-55Q23", "region": "NA", "firmware": "2.9.0",
                        "state": "standby", "utc_offset_min": -300, "downloads": 0, "last_seen": None})
        self.set_fixture("devices", devices)
        labels = {}
        for device_id in ("TV-NA", "TV-006", "TV-004"):  # NA, EU, APAC
            status, screen = self.screen(device_id)
            self.assertEqual(status, 200, device_id)
            labels[device_id] = [t["label"] for t in blocks(screen, "tile")]
        self.assertEqual(labels["TV-NA"], labels["TV-006"])
        self.assertEqual(labels["TV-006"], labels["TV-004"])

    def test_empty_list_says_no_stations(self):
        status, screen = self.screen(api=Api(self.store, stations=StaticStations([])))
        self.assertEqual(status, 200)
        self.assertEqual(blocks(screen, "grid"), [])
        self.assertIn("Brak dostępnych stacji, spróbuj później", [b["text"] for b in blocks(screen, "text")])
        self.assertIsNone(screen["focus"])

    def test_other_apps_keep_the_default_screen(self):
        status, screen = self.api.handle("GET", "/api/devices/TV-006/apps/kidsclub/screen")
        self.assertEqual(status, 200)
        self.assertEqual(blocks(screen, "grid"), [])
        self.assertIn("Kids Club", [b["text"] for b in blocks(screen, "text")])

    def test_screen_requests_only_read_the_list_in_memory(self):
        calls = []

        class CountingStations(StaticStations):
            def current(self):
                calls.append(1)
                return super().current()

        api = Api(self.store, stations=CountingStations(STATIONS))
        for _ in range(3):
            self.screen(api=api)
        self.assertEqual(len(calls), 3)


class MusicBoxOverHttpTest(ServerTestCase):
    def make_stations(self):
        return StaticStations(STATIONS)

    def test_grid_over_http(self):
        status, screen = self.get_json("/api/devices/TV-006/apps/musicbox/screen")
        self.assertEqual(status, 200)
        self.assertEqual(len(blocks(screen, "tile")), 3)
        json.dumps(screen)
        self.assertTrue(re.search(r"station=a1$", blocks(screen, "tile")[0]["action"]["path"]))
