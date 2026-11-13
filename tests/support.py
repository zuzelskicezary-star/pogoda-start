"""Shared helpers: a throwaway store and a live server on a free port."""

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from backend.server import make_server
from backend.stations import StaticStations
from backend.storage import FIXTURES_DIR, JsonStore


class StoreTestCase(unittest.TestCase):
    """Each test gets its own copy of ``fixtures/`` and an empty data directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        shutil.copytree(FIXTURES_DIR, root / "fixtures")
        self.store = JsonStore(data_dir=root / "data", fixtures_dir=root / "fixtures")

    def set_fixture(self, name, value):
        """Replace one fixture for this test only, e.g. the list of releases."""
        with open(self.store.fixtures_dir / (name + ".json"), "w", encoding="utf-8") as f:
            json.dump(value, f)


class ServerTestCase(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.server = make_server(self.store, port=0, quiet=True, stations=self.make_stations())
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base_url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def make_stations(self):
        """The Music Box station source; override to serve test stations."""
        return StaticStations()

    def request(self, method, path, body=None):
        """Return (status, headers, raw bytes)."""
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.headers, res.read()
        except urllib.error.HTTPError as err:
            return err.code, err.headers, err.read()

    def get_json(self, path):
        status, _, raw = self.request("GET", path)
        return status, json.loads(raw.decode("utf-8"))

    def post_json(self, path, body):
        status, _, raw = self.request("POST", path, body)
        return status, json.loads(raw.decode("utf-8"))
