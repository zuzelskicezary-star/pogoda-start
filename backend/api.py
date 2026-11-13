"""JSON API used by the TVs.

Every handler takes plain Python values and returns ``(status, payload)``,
so the API can be exercised without an HTTP server.
"""

import re

from backend import musicbox
from backend.musicbox import StationNotFound
from backend.catalog import get_apps_for_device
from backend.ota import OtaService, UnknownBuild
from backend.registry import DeviceNotFound, DeviceRegistry
from backend.screens import AppNotFound, build_screen
from backend.stations import StaticStations


class Api:
    def __init__(self, store, stations=None):
        self.store = store
        self.stations = stations if stations is not None else StaticStations()
        self.screens = {musicbox.APP_ID: musicbox.MusicBox(self.stations).screen}
        self.registry = DeviceRegistry(store)
        self.ota = OtaService(store, self.registry)
        self.routes = [
            ("GET", r"/api/health", self.health),
            ("GET", r"/api/devices", self.list_devices),
            ("GET", r"/api/devices/(?P<device_id>[\w-]+)", self.get_device),
            ("POST", r"/api/devices/(?P<device_id>[\w-]+)/report", self.report),
            ("GET", r"/api/devices/(?P<device_id>[\w-]+)/apps", self.device_apps),
            ("GET", r"/api/devices/(?P<device_id>[\w-]+)/apps/(?P<app_id>[\w-]+)/screen", self.app_screen),
            ("POST", r"/api/ota/check", self.ota_check),
            ("POST", r"/api/ota/download", self.ota_download),
        ]

    def handle(self, method, path, query=None, body=None):
        query = query or {}
        body = body or {}
        path_matched = False
        for route_method, pattern, handler in self.routes:
            match = re.fullmatch(pattern, path)
            if not match:
                continue
            path_matched = True
            if route_method != method:
                continue
            try:
                return handler(query=query, body=body, **match.groupdict())
            except DeviceNotFound as exc:
                return 404, {"error": "device_not_found", "device_id": exc.args[0]}
            except StationNotFound as exc:
                return 404, {"error": "station_not_found", "station": exc.args[0]}
            except AppNotFound as exc:
                return 404, {"error": "app_not_found", "app_id": exc.args[0]}
            except UnknownBuild as exc:
                return 404, {"error": "unknown_build", "build": exc.args[0]}
            except (KeyError, TypeError, ValueError) as exc:
                return 400, {"error": "bad_request", "detail": str(exc)}
        if path_matched:
            return 405, {"error": "method_not_allowed"}
        return 404, {"error": "not_found"}

    def health(self, query, body):
        return 200, {"status": "ok"}

    def list_devices(self, query, body):
        return 200, {"devices": self.registry.all()}

    def get_device(self, query, body, device_id):
        device = self.registry.get(device_id)
        model = self.registry.model(device["model"])
        details = dict(device)
        details.update(model)
        details["model_name"] = model["name"]
        details["model_year"] = model["year"]
        return 200, details

    def report(self, query, body, device_id):
        device = self.registry.report(
            device_id,
            firmware=body.get("firmware"),
            state=body.get("state"),
            utc_offset_min=body.get("utc_offset_min"),
        )
        return 200, device

    def device_apps(self, query, body, device_id):
        device = self.registry.get(device_id)
        return 200, {"device_id": device_id, "apps": get_apps_for_device(self.store, device)}

    def app_screen(self, query, body, device_id, app_id):
        device = self.registry.get(device_id)
        apps = get_apps_for_device(self.store, device)
        return 200, build_screen(device, apps, app_id, query, self.screens)

    def ota_check(self, query, body):
        update = self.ota.check(
            body["device_id"],
            firmware=body.get("firmware"),
            state=body.get("state"),
            utc_offset_min=body.get("utc_offset_min"),
        )
        return 200, {"update": update}

    def ota_download(self, query, body):
        return 200, self.ota.download(body["device_id"], body["build"])
