"""Station sources for Music Box.

A source has one narrow interface, ``current()``: the list of stations right
now, read from memory. Each station is ``{"id", "name", "logo", "stream"}``
(``logo`` may be None). Requests from TVs only ever call ``current()``; the
Radio Browser source refreshes itself in the background.
"""

import json
import sys
import threading
import urllib.request
from urllib.parse import urlencode

COUNTRY = "PL"
LIMIT = 20
REFRESH_S = 15 * 60
SERVER = "de1.api.radio-browser.info"
USER_AGENT = "LumioTV/1.0"
TIMEOUT_S = 10


class StaticStations:
    """A fixed list, e.g. in tests or when no network source is wanted."""

    def __init__(self, stations=()):
        self._stations = list(stations)

    def current(self):
        return list(self._stations)


def urllib_transport(url, headers, timeout):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class RadioBrowserStations:
    """The most voted working stations of one country, from Radio Browser.

    ``transport(url, headers, timeout) -> bytes`` does the HTTP GET, so tests
    substitute a fake and never touch the network.
    """

    def __init__(self, transport=urllib_transport, server=SERVER, country=COUNTRY, limit=LIMIT,
                 refresh_s=REFRESH_S):
        self.transport = transport
        self.server = server
        self.country = country
        self.limit = limit
        self.refresh_s = refresh_s
        self._stations = []
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def current(self):
        with self._lock:
            return list(self._stations)

    def refresh(self):
        """Fetch the list once and keep it in memory."""
        stations = self._fetch()
        with self._lock:
            self._stations = stations

    def start(self):
        """Refresh now and then every ``refresh_s`` seconds, in a daemon thread."""
        thread = threading.Thread(target=self._loop, name="stations", daemon=True)
        thread.start()
        return thread

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception as exc:  # keep refreshing; a bad round must not kill the thread
                sys.stderr.write("Radio Browser: %s\n" % exc)
            self._stop.wait(self.refresh_s)

    def _fetch(self):
        query = urlencode({
            "countrycode": self.country,
            "hidebroken": "true",
            "order": "votes",
            "reverse": "true",
            "limit": self.limit,
        })
        url = "https://%s/json/stations/search?%s" % (self.server, query)
        raw = self.transport(url, {"User-Agent": USER_AGENT}, TIMEOUT_S)
        return [s for s in map(_station, json.loads(raw.decode("utf-8"))) if s]


def _station(item):
    if not item.get("stationuuid") or not item.get("url_resolved"):
        return None
    return {
        "id": item["stationuuid"],
        "name": (item.get("name") or "").strip() or item["stationuuid"],
        "logo": item.get("favicon") or None,
        "stream": item["url_resolved"],
    }
