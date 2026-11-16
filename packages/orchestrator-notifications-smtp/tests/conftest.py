"""A minimal SMTP server on the standard library, for the SMTP channel tests."""

from __future__ import annotations

import base64
import socketserver
import threading
from collections.abc import Iterator

import pytest


class FakeSmtpServer(socketserver.ThreadingTCPServer):
    """Speaks just enough SMTP for smtplib: EHLO, AUTH, MAIL, RCPT, DATA, QUIT."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.messages: list[str] = []
        self.auth: list[tuple[str, str]] = []
        self.refuse_recipients = False
        self.fail_auth = False
        self.silent = False
        self.release = threading.Event()
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    def start(self) -> FakeSmtpServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self.release.set()
        self.shutdown()
        self.server_close()
        self._thread.join(timeout=5)


class _Handler(socketserver.StreamRequestHandler):
    server: FakeSmtpServer

    def handle(self) -> None:  # noqa: PLR0912 - one branch per SMTP verb
        if self.server.silent:
            self.server.release.wait(10)  # keep the connection open, never greet
            return
        self._reply("220 fake.smtp ESMTP")
        data: list[str] | None = None
        while raw := self.rfile.readline():
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if data is not None:
                if line == ".":
                    self.server.messages.append("\n".join(data))
                    data = None
                    self._reply("250 2.0.0 queued")
                else:
                    data.append(line[1:] if line.startswith("..") else line)
                continue
            verb, _, rest = line.partition(" ")
            verb = verb.upper()
            if verb == "EHLO":
                self._reply("250-fake.smtp")
                self._reply("250-AUTH PLAIN LOGIN XOAUTH2")
                self._reply("250 8BITMIME")
            elif verb == "HELO":
                self._reply("250 fake.smtp")
            elif verb == "AUTH":
                mechanism, _, payload = rest.partition(" ")
                decoded = base64.b64decode(payload).decode("utf-8") if payload else ""
                self.server.auth.append((mechanism.upper(), decoded))
                self._reply("535 5.7.8 rejected" if self.server.fail_auth else "235 2.7.0 ok")
            elif verb == "MAIL":
                self._reply("250 2.1.0 ok")
            elif verb == "RCPT":
                refused = self.server.refuse_recipients
                self._reply("550 5.1.1 <operacao@exemplo.com> unknown" if refused else "250 ok")
            elif verb == "DATA":
                data = []
                self._reply("354 end with .")
            elif verb == "QUIT":
                self._reply("221 2.0.0 bye")
                return
            elif verb in {"RSET", "NOOP"}:
                self._reply("250 ok")
            else:
                self._reply("502 5.5.2 not implemented")

    def _reply(self, text: str) -> None:
        self.wfile.write(f"{text}\r\n".encode())
        self.wfile.flush()


@pytest.fixture
def smtp_server() -> Iterator[FakeSmtpServer]:
    server = FakeSmtpServer().start()
    try:
        yield server
    finally:
        server.stop()
