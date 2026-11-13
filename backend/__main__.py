"""Run the backend: ``python -m backend [--port 8765] [--reset]``."""

import argparse
import os

from backend.server import make_server
from backend import stations as stations_settings
from backend.stations import RadioBrowserStations
from backend.storage import JsonStore


def main():
    parser = argparse.ArgumentParser(prog="python -m backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TV_PORT", "8765")))
    parser.add_argument("--reset", action="store_true", help="restore the device registry from fixtures")
    parser.add_argument("--stations-country", default=stations_settings.COUNTRY,
                        help="Music Box: country code of the stations (default %(default)s)")
    parser.add_argument("--stations-limit", type=int, default=stations_settings.LIMIT,
                        help="Music Box: number of stations (default %(default)s)")
    args = parser.parse_args()

    store = JsonStore()
    if args.reset:
        store.reset()
    stations = RadioBrowserStations(country=args.stations_country, limit=args.stations_limit)
    stations.start()
    server = make_server(store, host=args.host, port=args.port, stations=stations)
    base = "http://localhost:%d" % server.server_address[1]
    print("Lumio TV backend: %s/api/health" % base)
    print("Telewizory:       %s/tv/?device=TV-001  (TV-001 ... TV-007)" % base)
    print("Ctrl+C zatrzymuje serwer.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
