"""Static file server for the UI preview.

This is a temporary host so the interface can be opened from a container before the
real FastAPI application exists (`app/main.py`, milestone M4). It serves files from
`static/` only, maps `/` to `index.html`, and never serves anything outside that
directory.

When the backend lands, `app/main.py` mounts the same `static/` directory and this
module is deleted; no UI file needs to change.
"""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import unquote, urlsplit

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
DEFAULT_PORT = 8000


class StaticUIHandler(SimpleHTTPRequestHandler):
    """Serves `static/` and nothing else, with explicit UTF-8 types."""

    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args: object, directory: str | None = None, **kwargs: object) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self, *args: object, **kwargs: object) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            self.path = "/index.html"
        if path.startswith("/api/"):
            self._send_missing_api(path)
            return
        super().do_GET(*args, **kwargs)

    def _send_missing_api(self, path: str) -> None:
        body = (
            b'{"error":{"code":"not_implemented",'
            b'"message":"Endpoint API belum tersedia pada pratinjau UI.",'
            b'"details":null}}'
        )
        self.send_response(501)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        # The preview must not serve a stale stylesheet after a rebuild.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        super().log_message("%s - " + format, self.address_string(), *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the static UI preview.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), StaticUIHandler)
    print(f"UI preview: http://localhost:{args.port}/ (statis dari {STATIC_DIR})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
