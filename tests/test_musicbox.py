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


class ChangingStations:
    """A source whose list the test replaces, like a background refresh would."""

    def __init__(self, stations):
        self.stations = list(stations)

    def current(self):
        return list(self.stations)


def by_id(screen, block_id):
    (found,) = [b for b in walk(screen["root"]) if b.get("id") == block_id]
    return found


def player_path(device_id, uuid):
    return "/api/devices/%s/apps/musicbox/screen?station=%s" % (device_id, uuid)


def go(uuid, device_id="TV-006"):
    return {"type": "open_screen", "path": player_path(device_id, uuid), "replace": True}


class MusicBoxPlayerTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.stations = ChangingStations(STATIONS)
        self.api = Api(self.store, stations=self.stations)

    def player(self, uuid, device_id="TV-006"):
        return self.api.handle("GET", "/api/devices/%s/apps/musicbox/screen" % device_id, {"station": uuid})

    def test_player_plays_the_station_stream(self):
        status, screen = self.player("b2")
        self.assertEqual(status, 200)
        self.assertEqual(screen["stream"]["url"], "https://stream.example/b2")
        self.assertTrue(screen["stream"]["error"])

    def test_player_shows_name_and_logo(self):
        _, screen = self.player("a1")
        self.assertIn("RMF FM", [b["text"] for b in blocks(screen, "text")])
        self.assertIn("https://logo.example/a1.png", [b["url"] for b in blocks(screen, "image")])

    def test_focus_starts_on_play_pause(self):
        _, screen = self.player("a1")
        self.assertEqual(screen["focus"], "playpause")
        self.assertEqual(by_id(screen, "playpause")["action"], {"type": "toggle_pause"})

    def test_volume_buttons_step_ten_percent(self):
        _, screen = self.player("a1")
        self.assertEqual(by_id(screen, "volume-down")["action"], {"type": "volume", "step": -10})
        self.assertEqual(by_id(screen, "volume-up")["action"], {"type": "volume", "step": 10})

    def test_back_button_goes_back_to_the_grid(self):
        _, screen = self.player("a1")
        self.assertEqual(by_id(screen, "back")["action"], {"type": "back"})

    def test_previous_and_next_station(self):
        _, screen = self.player("b2")
        self.assertEqual(by_id(screen, "prev")["action"], go("a1"))
        self.assertEqual(by_id(screen, "next")["action"], go("c3"))

    def test_previous_and_next_wrap_around(self):
        _, first = self.player("a1")
        _, last = self.player("c3")
        self.assertEqual(by_id(first, "prev")["action"], go("c3"))
        self.assertEqual(by_id(last, "next")["action"], go("a1"))

    def test_channel_keys_switch_stations(self):
        _, screen = self.player("b2", device_id="TV-004")
        self.assertEqual(screen["keys"], {"chup": go("c3", "TV-004"), "chdown": go("a1", "TV-004")})

    def test_list_holds_the_other_stations(self):
        _, screen = self.player("b2")
        (station_list,) = blocks(screen, "list")
        self.assertEqual([i["label"] for i in station_list["children"]], ["RMF FM", "Polskie Radio Trójka"])
        self.assertEqual([i["action"] for i in station_list["children"]], [go("a1"), go("c3")])

    def test_station_that_fell_out_of_the_list_keeps_playing(self):
        self.player("b2")
        self.stations.stations = [station("d4", "Antyradio"), station("a1", "RMF FM")]
        status, screen = self.player("b2")
        self.assertEqual(status, 200)
        self.assertEqual(screen["stream"]["url"], "https://stream.example/b2")
        self.assertEqual(by_id(screen, "next")["action"], go("d4"))
        self.assertEqual(by_id(screen, "prev")["action"], go("a1"))
        self.assertEqual([i["label"] for i in blocks(screen, "list")[0]["children"]], ["Antyradio", "RMF FM"])

    def test_station_seen_only_on_the_grid_is_remembered(self):
        self.api.handle("GET", "/api/devices/TV-006/apps/musicbox/screen")
        self.stations.stations = []
        status, screen = self.player("c3")
        self.assertEqual(status, 200)
        self.assertEqual(blocks(screen, "list")[0]["children"], [])

    def test_unknown_station_is_404(self):
        status, body = self.player("nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "station_not_found")

    def test_player_refreshes_every_minute(self):
        _, screen = self.player("a1")
        self.assertEqual(screen["refresh"], 60)

    def test_grid_tiles_push_the_player(self):
        _, grid_screen = self.api.handle("GET", "/api/devices/TV-006/apps/musicbox/screen")
        self.assertNotIn("replace", blocks(grid_screen, "tile")[0]["action"])
        self.assertNotIn("stream", grid_screen)


class MusicBoxPlayerOverHttpTest(ServerTestCase):
    def make_stations(self):
        return StaticStations(STATIONS)

    def test_player_over_http(self):
        status, screen = self.get_json("/api/devices/TV-006/apps/musicbox/screen?station=c3")
        self.assertEqual(status, 200)
        self.assertEqual(screen["stream"]["url"], "https://stream.example/c3")
        status, body = self.get_json("/api/devices/TV-006/apps/musicbox/screen?station=zzz")
        self.assertEqual((status, body["error"]), (404, "station_not_found"))


FAVOURITES_PATH = "/api/devices/%s/apps/musicbox/favourites"


def favourite(uuid, on=True, device_id="TV-006"):
    return {"type": "post", "path": FAVOURITES_PATH % device_id, "body": {"station": uuid, "favourite": on}}


class MusicBoxFavouritesTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.api = Api(self.store, stations=StaticStations(STATIONS))

    def player(self, uuid, device_id="TV-006", api=None):
        return (api or self.api).handle(
            "GET", "/api/devices/%s/apps/musicbox/screen" % device_id, {"station": uuid})[1]

    def grid(self, device_id="TV-006"):
        return self.api.handle("GET", "/api/devices/%s/apps/musicbox/screen" % device_id)[1]

    def mark(self, uuid, on=True, device_id="TV-006"):
        return self.api.handle("POST", FAVOURITES_PATH % device_id, body={"station": uuid, "favourite": on})

    def test_player_offers_to_add_the_station(self):
        button = by_id(self.player("a1"), "favourite")
        self.assertEqual(button["label"], "☆ Dodaj do ulubionych")
        self.assertEqual(button["action"], favourite("a1"))

    def test_adding_marks_the_station_with_a_star(self):
        self.assertEqual(self.mark("a1"), (200, {"station": "a1", "favourite": True}))
        self.assertEqual([t["label"] for t in blocks(self.grid(), "tile")],
                         ["★ RMF FM", "Radio ZET", "Polskie Radio Trójka"])
        other_list = blocks(self.player("b2"), "list")[0]["children"]
        self.assertEqual([i["label"] for i in other_list], ["★ RMF FM", "Polskie Radio Trójka"])

    def test_same_button_removes_the_station(self):
        self.mark("a1")
        button = by_id(self.player("a1"), "favourite")
        self.assertEqual(button["label"], "★ Usuń z ulubionych")
        self.assertEqual(button["action"], favourite("a1", on=False))
        self.assertEqual(self.mark("a1", on=False), (200, {"station": "a1", "favourite": False}))
        self.assertEqual(blocks(self.grid(), "tile")[0]["label"], "RMF FM")

    def test_star_does_not_change_order_or_fallback_text(self):
        self.mark("c3")
        tiles = blocks(self.grid(), "tile")
        self.assertEqual([t["id"] for t in tiles], ["station-a1", "station-b2", "station-c3"])
        self.assertEqual(tiles[2]["image"]["text"], "Polskie Radio Trójka")

    def test_favourites_belong_to_one_tv(self):
        self.mark("a1", device_id="TV-006")
        self.assertEqual(blocks(self.grid("TV-004"), "tile")[0]["label"], "RMF FM")

    def test_favourites_survive_a_restart(self):
        self.mark("b2")
        restarted = Api(self.store, stations=StaticStations(STATIONS))
        self.assertEqual(by_id(self.player("b2", api=restarted), "favourite")["label"], "★ Usuń z ulubionych")

    def test_marking_twice_is_harmless(self):
        self.mark("a1")
        self.mark("a1")
        self.mark("a1", on=False)
        self.assertEqual(blocks(self.grid(), "tile")[0]["label"], "RMF FM")

    def test_unknown_station_is_404(self):
        status, body = self.mark("nope")
        self.assertEqual((status, body["error"]), (404, "station_not_found"))

    def test_unknown_tv_or_hidden_app_is_404(self):
        self.assertEqual(self.mark("a1", device_id="TV-999")[1]["error"], "device_not_found")
        self.assertEqual(self.mark("a1", device_id="TV-001")[1]["error"], "app_not_found")  # FW too old

    def test_missing_fields_are_400(self):
        self.assertEqual(self.api.handle("POST", FAVOURITES_PATH % "TV-006", body={"favourite": True})[0], 400)
        self.assertEqual(self.api.handle("POST", FAVOURITES_PATH % "TV-006", body={"station": "a1"})[0], 400)


class MusicBoxFavouritesOverHttpTest(ServerTestCase):
    def make_stations(self):
        return StaticStations(STATIONS)

    def test_add_over_http(self):
        status, body = self.post_json(FAVOURITES_PATH % "TV-006", {"station": "b2", "favourite": True})
        self.assertEqual((status, body), (200, {"station": "b2", "favourite": True}))
        _, screen = self.get_json("/api/devices/TV-006/apps/musicbox/screen")
        self.assertEqual(blocks(screen, "tile")[1]["label"], "★ Radio ZET")
