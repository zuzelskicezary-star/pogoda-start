"""App screens described by the backend (ADR 0001), seen through the API."""

from backend.api import Api
from tests.support import ServerTestCase, StoreTestCase


def walk(block):
    yield block
    for child in block.get("children", []):
        yield from walk(child)


def texts(screen):
    return [b["text"] for b in walk(screen["root"]) if b["type"] == "text"]


class DefaultScreenTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.api = Api(self.store)

    def screen(self, device_id, app_id, query=None):
        return self.api.handle("GET", "/api/devices/%s/apps/%s/screen" % (device_id, app_id), query)

    def test_app_without_own_screen_shows_its_name(self):
        status, screen = self.screen("TV-001", "streamly")
        self.assertEqual(status, 200)
        self.assertEqual(screen["app_id"], "streamly")
        self.assertIn("Streamly", texts(screen))

    def test_default_screen_refreshes_every_minute(self):
        _, screen = self.screen("TV-001", "news24")
        self.assertEqual(screen["refresh"], 60)

    def test_default_screen_has_no_focus_and_leaves_channels_alone(self):
        _, screen = self.screen("TV-001", "news24")
        self.assertIsNone(screen["focus"])
        self.assertEqual(screen["keys"], {})

    def test_root_is_a_layout_block(self):
        _, screen = self.screen("TV-001", "gallery")
        self.assertIn(screen["root"]["type"], ("row", "column"))
        for block in walk(screen["root"]):
            self.assertIn(block["type"], ("row", "column", "text", "button"))

    def test_screen_params_are_accepted(self):
        status, screen = self.screen("TV-001", "news24", {"station": "abc"})
        self.assertEqual(status, 200)
        self.assertIn("News 24", texts(screen))

    def test_unknown_device_is_404(self):
        status, body = self.screen("TV-999", "streamly")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "device_not_found")

    def test_unknown_app_is_404(self):
        status, body = self.screen("TV-001", "nope")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "app_not_found")

    def test_app_outside_the_devices_region_is_404(self):
        status, body = self.screen("TV-001", "kinonet")  # EU only, TV-001 is NA
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "app_not_found")

    def test_app_needing_newer_firmware_is_404(self):
        status, _ = self.screen("TV-001", "musicbox")  # needs FW 2.9, TV-001 has 2.8.1
        self.assertEqual(status, 404)
        status, _ = self.screen("TV-006", "musicbox")
        self.assertEqual(status, 200)

    def test_hidden_app_is_404(self):
        status, body = self.screen("TV-001", "diagnostics")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "app_not_found")

    def test_post_is_not_allowed(self):
        status, _ = self.api.handle("POST", "/api/devices/TV-001/apps/streamly/screen")
        self.assertEqual(status, 405)


class ScreenOverHttpTest(ServerTestCase):
    def test_screen_endpoint(self):
        status, screen = self.get_json("/api/devices/TV-004/apps/musicbox/screen?station=x")
        self.assertEqual(status, 200)
        self.assertTrue({"app_id", "refresh", "focus", "keys", "root"} <= set(screen))
        self.assertIn("Music Box", texts(screen))

    def test_screen_errors(self):
        self.assertEqual(self.get_json("/api/devices/TV-999/apps/musicbox/screen")[0], 404)
        self.assertEqual(self.get_json("/api/devices/TV-001/apps/musicbox/screen")[0], 404)
