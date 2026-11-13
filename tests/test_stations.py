"""The Radio Browser boundary, with a fake HTTP transport (no network)."""

import json
import unittest
from urllib.parse import parse_qs, urlparse

from backend.stations import RadioBrowserStations


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
        transport = FakeTransport([])
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
