"""The Radio Browser boundary, with a fake HTTP transport (no network)."""

import json
import socket
import unittest
from urllib.parse import parse_qs, urlparse

from backend.stations import RadioBrowserStations
from tests.support import StoreTestCase


def rb_station(uuid, name, url="https://stream.example/%s", favicon="https://logo.example/%s.png"):
    return {
        "stationuuid": uuid,
        "name": name,
        "url": "http://playlist.example/%s.m3u" % uuid,
        "url_resolved": url % uuid if url else "",
        "favicon": favicon % uuid if favicon else "",
        "votes": 100,
        "countrycode": "PL",
    }


class FakeTransport:
    def __init__(self, body):
        self.body = body
        self.requests = []

    def __call__(self, url, headers, timeout):
        self.requests.append({"url": url, "headers": headers, "timeout": timeout})
        return json.dumps(self.body).encode("utf-8")


class RadioBrowserStationsTest(unittest.TestCase):
    def test_starts_empty_until_first_refresh(self):
        source = RadioBrowserStations(transport=FakeTransport([]))
        self.assertEqual(source.current(), [])

    def test_asks_for_most_voted_working_stations_of_the_country(self):
        transport = FakeTransport([rb_station("u1", "RMF FM")])
        RadioBrowserStations(transport=transport, country="PL", limit=20).refresh()
        (request,) = transport.requests
        url = urlparse(request["url"])
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.path, "/json/stations/search")
        self.assertEqual(parse_qs(url.query), {
            "countrycode": ["PL"], "hidebroken": ["true"], "order": ["votes"], "reverse": ["true"], "limit": ["20"],
        })

    def test_count_and_country_are_settings(self):
        transport = FakeTransport([])
        RadioBrowserStations(transport=transport, country="CZ", limit=5).refresh()
        query = parse_qs(urlparse(transport.requests[0]["url"]).query)
        self.assertEqual((query["countrycode"], query["limit"]), (["CZ"], ["5"]))

    def test_introduces_itself_with_a_generic_user_agent(self):
        transport = FakeTransport([])
        RadioBrowserStations(transport=transport).refresh()
        self.assertEqual(transport.requests[0]["headers"]["User-Agent"], "LumioTV/1.0")

    def test_keeps_order_and_maps_fields(self):
        source = RadioBrowserStations(transport=FakeTransport([
            rb_station("u1", "RMF FM"), rb_station("u2", "Radio ZET", favicon=None),
        ]))
        source.refresh()
        self.assertEqual(source.current(), [
            {"id": "u1", "name": "RMF FM", "logo": "https://logo.example/u1.png", "stream": "https://stream.example/u1"},
            {"id": "u2", "name": "Radio ZET", "logo": None, "stream": "https://stream.example/u2"},
        ])

    def test_skips_stations_without_a_stream(self):
        source = RadioBrowserStations(transport=FakeTransport([
            rb_station("u1", "Bez strumienia", url=None), rb_station("u2", "Radio ZET"),
        ]))
        source.refresh()
        self.assertEqual([s["id"] for s in source.current()], ["u2"])

    def test_reading_the_list_never_calls_radio_browser(self):
        transport = FakeTransport([rb_station("u1", "RMF FM")])
        source = RadioBrowserStations(transport=transport)
        source.refresh()
        for _ in range(5):
            source.current()
        self.assertEqual(len(transport.requests), 1)

    def test_current_returns_a_copy(self):
        source = RadioBrowserStations(transport=FakeTransport([rb_station("u1", "RMF FM")]))
        source.refresh()
        source.current().clear()
        self.assertEqual(len(source.current()), 1)


class FlakyTransport:
    """Answers per server: an exception to raise or a body to return."""

    def __init__(self, answers):
        self.answers = answers
        self.hosts = []

    def __call__(self, url, headers, timeout):
        host = urlparse(url).hostname
        self.hosts.append(host)
        answer = self.answers.get(host, OSError("no route to %s" % host))
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, bytes):
            return answer
        return json.dumps(answer).encode("utf-8")


FAKE_SERVERS = ["one.example", "two.example", "three.example"]
GOOD = [rb_station("u1", "RMF FM"), rb_station("u2", "Radio ZET")]


class MirrorFailoverTest(unittest.TestCase):
    def source(self, answers, **kwargs):
        transport = FlakyTransport(answers)
        return RadioBrowserStations(transport=transport, servers=FAKE_SERVERS, **kwargs), transport

    def test_failing_server_falls_over_to_the_next(self):
        source, transport = self.source({"two.example": GOOD})
        self.assertTrue(source.refresh())
        self.assertEqual(transport.hosts, ["one.example", "two.example"])
        self.assertEqual([s["id"] for s in source.current()], ["u1", "u2"])

    def test_timeout_and_garbage_count_as_failures(self):
        source, transport = self.source({
            "one.example": socket.timeout("timed out"),
            "two.example": b"<html>502 Bad Gateway</html>",
            "three.example": GOOD,
        })
        self.assertTrue(source.refresh())
        self.assertEqual(transport.hosts, FAKE_SERVERS)
        self.assertEqual(len(source.current()), 2)

    def test_stops_at_the_first_server_that_answers(self):
        source, transport = self.source({"one.example": GOOD, "two.example": GOOD})
        source.refresh()
        self.assertEqual(transport.hosts, ["one.example"])

    def test_failed_refresh_keeps_the_last_good_list(self):
        source, transport = self.source({"one.example": GOOD})
        source.refresh()
        transport.answers = {}
        self.assertFalse(source.refresh())
        self.assertEqual([s["id"] for s in source.current()], ["u1", "u2"])

    def test_empty_answer_keeps_the_last_good_list(self):
        source, transport = self.source({"one.example": GOOD})
        source.refresh()
        transport.answers = {"one.example": [], "two.example": []}
        self.assertFalse(source.refresh())
        self.assertEqual(len(source.current()), 2)


class SavedCopyTest(StoreTestCase):
    def source(self, answers):
        return self.source_and_transport(answers)[0]

    def source_and_transport(self, answers):
        transport = FlakyTransport(answers)
        return RadioBrowserStations(transport=transport, servers=FAKE_SERVERS, store=self.store), transport

    def test_first_start_without_network_or_copy_has_no_stations(self):
        source = self.source({})
        self.assertFalse(source.refresh())
        self.assertEqual(source.current(), [])

    def test_restart_during_outage_starts_from_the_saved_copy(self):
        self.source({"one.example": GOOD}).refresh()
        restarted = self.source({})
        self.assertEqual([s["id"] for s in restarted.current()], ["u1", "u2"])
        self.assertFalse(restarted.refresh())
        self.assertEqual(len(restarted.current()), 2)

    def test_copy_is_read_before_any_fetch(self):
        self.source({"one.example": GOOD}).refresh()
        restarted, transport = self.source_and_transport({})
        self.assertEqual(len(restarted.current()), 2)
        self.assertEqual(transport.hosts, [])

    def test_every_good_list_replaces_the_copy(self):
        self.source({"one.example": GOOD}).refresh()
        self.source({"one.example": [rb_station("u9", "Antyradio")]}).refresh()
        self.assertEqual([s["id"] for s in self.source({}).current()], ["u9"])

    def test_reset_keeps_the_copy(self):
        self.source({"one.example": GOOD}).refresh()
        self.store.reset()
        self.assertEqual(len(self.source({}).current()), 2)

    def test_damaged_copy_starts_empty(self):
        self.store.data_dir.mkdir(parents=True, exist_ok=True)
        (self.store.data_dir / "stations.json").write_text('[{"id": "u1", "na', encoding="utf-8")
        source = self.source({"one.example": GOOD})
        self.assertEqual(source.current(), [])
        self.assertTrue(source.refresh())
        self.assertEqual(len(source.current()), 2)

    def test_failed_refresh_leaves_the_copy_alone(self):
        self.source({"one.example": GOOD}).refresh()
        self.source({}).refresh()
        self.assertEqual(len(self.source({}).current()), 2)
