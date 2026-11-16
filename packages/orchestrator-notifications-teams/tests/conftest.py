"""A local HTTP server on the standard library, standing in for a Teams Workflows webhook."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class FakeWebhook(ThreadingHTTPServer):
    """Records the POST bodies; can answer another status, redirect or never answer."""

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.bodies: list[str] = []
        self.paths: list[str] = []
        self.status = 202
        self.redirect_to: str | None = None
        self.silent = False
        self.release = threading.Event()
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def start(self) -> FakeWebhook:
        self._thread.start()
        return self

    def stop(self) -> None:
        self.release.set()
        self.shutdown()
        self.server_close()
        self._thread.join(timeout=5)


class _Handler(BaseHTTPRequestHandler):
    server: FakeWebhook

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        self.server.paths.append(self.path)
        if self.server.silent:
            self.server.release.wait(10)
            return
        if self.server.redirect_to is not None:
            self.send_response(302)
            self.send_header("Location", self.server.redirect_to)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.server.bodies.append(body)
        self.send_response(self.server.status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        return


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    server = FakeWebhook().start()
    try:
        yield server
    finally:
        server.stop()
