"""HTTP server: serves the TV simulator from ``tv/`` and the JSON API."""

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from backend.api import Api
from backend.storage import REPO_ROOT

TV_DIR = REPO_ROOT / "tv"
MAX_BODY_BYTES = 64 * 1024


def make_server(store, host="127.0.0.1", port=8765, tv_dir=TV_DIR, quiet=False, stations=None):
    api = Api(store, stations=stations)

    class Handler(BaseHTTPRequestHandler):
        server_version = "LumioBackend/1.0"

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def _dispatch(self, method):
            url = urlparse(self.path)
            if url.path.startswith("/api/"):
                self._api(method, url)
            elif method == "GET" and url.path in ("/", "/tv"):
                self.send_response(302)
                self.send_header("Location", "/tv/" + ("?" + url.query if url.query else ""))
                self.end_headers()
            elif method == "GET" and url.path.startswith("/tv/"):
                self._static(url.path[len("/tv/"):])
            else:
                self._json(404, {"error": "not_found"})

        def _api(self, method, url):
            body = {}
            if method == "POST":
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY_BYTES:
                    self._json(413, {"error": "body_too_large"})
                    return
                raw = self.rfile.read(length) if length else b""
                if raw:
                    try:
                        body = json.loads(raw.decode("utf-8"))
                    except ValueError:
                        self._json(400, {"error": "invalid_json"})
                        return
                if not isinstance(body, dict):
                    self._json(400, {"error": "invalid_json"})
                    return
            query = {k: v[-1] for k, v in parse_qs(url.query).items()}
            status, payload = api.handle(method, url.path, query, body)
            self._json(status, payload)

        def _static(self, relative):
            root = Path(tv_dir).resolve()
            target = (root / (relative or "index.html")).resolve()
            if root not in target.parents and target != root:
                self._json(404, {"error": "not_found"})
                return
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                self._json(404, {"error": "not_found"})
                return
            data = target.read_bytes()
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype == "application/javascript":
                ctype += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status, payload):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            if not quiet:
                sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
