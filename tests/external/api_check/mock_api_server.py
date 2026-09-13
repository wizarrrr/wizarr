"""A reusable mock of the external API that gates wizard progression.

Wizarr's ``{{ widget:api_check }}`` gate calls an admin-configured endpoint and
lets the user continue only when it answers with an expected status code. This
module stands in for that endpoint so tests (and other developers) can drive the
gate without a real service.

It is a real HTTP server on loopback, not a monkeypatch, so it exercises the
whole ``requests`` path including timeouts, redirects and connection errors.

Wizarr signs each request as::

    canonical = "v1\\n{timestamp}\\n{nonce}\\n{METHOD}\\n{url_path}\\n{code}\\n{username}\\n{email}"
    X-Wizarr-Signature: sha256=<hmac_sha256(api_key, canonical).hexdigest()>

alongside ``X-Wizarr-Timestamp`` and ``X-Wizarr-Nonce``. Pass ``hmac_secret`` to
have the mock verify that and expose the verdict on each recorded request.

Fixed paths, always available:

===========  ==========================================================
``/check``   the validating endpoint (the one you normally point Wizarr at)
``/boom``    always 500
``/slow``    sleeps ``delay`` seconds, then behaves like ``/check``
``/redirect``302 to ``/check`` – Wizarr must never follow it
``/teapot``  always 418, for non-default ``expect_status`` tests
===========  ==========================================================

Example::

    with MockApiServer(expect_code="ABC123", hmac_secret="s3cr3t") as api:
        api.program(403, 403, 200)          # fail twice, then pass
        ...                                  # drive the wizard
        assert api.request_count == 3
        assert api.last().signature_valid
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Self
from urllib.parse import parse_qs, urlsplit

SIGNATURE_VERSION = "v1"
DEFAULT_SKEW_TOLERANCE = 300


def build_canonical_string(
    *,
    timestamp: str,
    nonce: str,
    method: str,
    path: str,
    code: str,
    username: str,
    email: str,
) -> str:
    """Return the exact string Wizarr signs. Kept here so the mock and the app
    can be tested against one another rather than against a shared helper."""
    return "\n".join(
        [
            SIGNATURE_VERSION,
            timestamp,
            nonce,
            method.upper(),
            path,
            code,
            username,
            email,
        ]
    )


def sign(secret: str, canonical: str) -> str:
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class RecordedRequest:
    """One request the mock received, captured for assertions."""

    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: dict[str, Any] | None
    signature_valid: bool | None
    signature_error: str
    received_at: float
    code: str | None
    username: str | None
    email: str | None


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: MockApiServer._Server  # type: ignore[name-defined]

    def log_message(self, *_args):  # keep pytest output clean
        pass

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _handle(self, method: str):
        api: MockApiServer = self.server.api
        parts = urlsplit(self.path)
        query = parse_qs(parts.query, keep_blank_values=True)

        if api.control_enabled and parts.path.startswith("/_control"):
            self._handle_control(api, parts.path)
            return

        body = None
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode())
            except (ValueError, UnicodeDecodeError):
                body = None

        status = api._record_and_decide(
            method, parts.path, query, dict(self.headers), body
        )
        payload = json.dumps({"ok": status < 400}).encode()

        try:
            self.send_response(status)
            if status == 302:
                self.send_header("Location", f"{api.url}/check")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            # Client gave up first - expected whenever a test exercises a timeout.
            pass

    def _handle_control(self, api: MockApiServer, path: str):
        """Manual-testing surface: flip the answer without restarting."""
        if path == "/_control/pass":
            api.set_status(200)
        elif path == "/_control/fail":
            api.set_status(403)
        elif path.startswith("/_control/status/"):
            with contextlib.suppress(ValueError):
                api.set_status(int(path.rsplit("/", 1)[-1]))
        elif path == "/_control/reset":
            api.reset()

        body = api.control_page().encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


class MockApiServer:
    """Threaded stdlib HTTP server. Use as a context manager."""

    class _Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

        def __init__(self, addr, handler, api: MockApiServer):
            self.api = api
            super().__init__(addr, handler)

        def handle_error(self, request, client_address):
            pass  # a disconnecting client is normal here, not a test failure

    def __init__(
        self,
        *,
        status: int = 200,
        fail_status: int = 403,
        expect_code: str | None = None,
        expect_username: str | None = None,
        expect_email: str | None = None,
        code_param: str = "code",
        username_param: str = "username",
        email_param: str = "email",
        hmac_secret: str | None = None,
        auth_header: str | None = None,
        auth_value: str | None = None,
        delay: float = 0.0,
        clock_skew_tolerance: int = DEFAULT_SKEW_TOLERANCE,
        control_enabled: bool = False,
    ) -> None:
        self._status = status
        self._fail_status = fail_status
        self._expect_code = expect_code
        self._expect_username = expect_username
        self._expect_email = expect_email
        self._code_param = code_param
        self._username_param = username_param
        self._email_param = email_param
        self._hmac_secret = hmac_secret
        self._auth_header = auth_header
        self._auth_value = auth_value
        self._delay = delay
        self._skew = clock_skew_tolerance
        self.control_enabled = control_enabled

        self._programmed: list[int] = []
        self._requests: list[RecordedRequest] = []
        self._lock = threading.Lock()
        self._server: MockApiServer._Server | None = None
        self._thread: threading.Thread | None = None

    # ── lifecycle ────────────────────────────────────────────────────
    def start(self) -> Self:
        self._server = MockApiServer._Server(("127.0.0.1", 0), _Handler, self)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    # ── addressing ───────────────────────────────────────────────────
    @property
    def port(self) -> int:
        assert self._server is not None, "MockApiServer is not started"
        return self._server.server_address[1]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def path(self, p: str = "/check") -> str:
        return f"{self.url}{p if p.startswith('/') else '/' + p}"

    # ── programmable behaviour ───────────────────────────────────────
    def set_status(self, code: int) -> None:
        with self._lock:
            self._status = code
            self._programmed.clear()

    def program(self, *statuses: int) -> None:
        """Queue statuses for successive hits; the last one repeats forever."""
        with self._lock:
            self._programmed = list(statuses)

    def set_delay(self, seconds: float) -> None:
        with self._lock:
            self._delay = seconds

    def set_expected(
        self,
        *,
        code: str | None = None,
        username: str | None = None,
        email: str | None = None,
    ) -> None:
        with self._lock:
            self._expect_code = code
            self._expect_username = username
            self._expect_email = email

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._programmed.clear()

    # ── assertions ───────────────────────────────────────────────────
    @property
    def requests(self) -> list[RecordedRequest]:
        with self._lock:
            return list(self._requests)

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    def last(self) -> RecordedRequest | None:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def control_page(self) -> str:
        """A tiny dashboard for driving the mock by hand during dev testing."""
        with self._lock:
            current = self._programmed[0] if self._programmed else self._status
            rows = "".join(
                f"<tr><td>{r.received_at:.0f}</td><td>{r.method}</td><td>{r.path}</td>"
                f"<td>{r.code or ''}</td><td>{r.username or ''}</td><td>{r.email or ''}</td>"
                f"<td>{'' if r.signature_valid is None else r.signature_valid}</td></tr>"
                for r in reversed(self._requests[-25:])
            )
            count = len(self._requests)
        state = "PASS" if current == 200 else f"FAIL ({current})"
        return f"""<!doctype html><meta charset=utf-8>
<title>Wizarr mock API</title>
<style>
 body{{font:14px/1.5 system-ui,sans-serif;margin:2rem;max-width:60rem}}
 a.btn{{display:inline-block;padding:.5rem 1rem;margin-right:.5rem;border-radius:.5rem;
        text-decoration:none;color:#fff}}
 .pass{{background:#16a34a}} .fail{{background:#dc2626}} .reset{{background:#525252}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem}}
 td,th{{border-bottom:1px solid #ddd;padding:.35rem .5rem;text-align:left;font-size:13px}}
 code{{background:#f4f4f5;padding:.1rem .3rem;border-radius:.25rem}}
</style>
<h1>Wizarr mock API</h1>
<p>Currently answering <strong>{state}</strong> on <code>/check</code> &mdash; {count} request(s) received.</p>
<p>
  <a class="btn pass" href="/_control/pass">Answer 200 (pass)</a>
  <a class="btn fail" href="/_control/fail">Answer 403 (fail)</a>
  <a class="btn reset" href="/_control/reset">Clear log</a>
</p>
<p>Fixed paths: <code>/check</code>, <code>/boom</code> (500), <code>/slow</code>,
   <code>/redirect</code> (302), <code>/teapot</code> (418).</p>
<table>
 <tr><th>at</th><th>method</th><th>path</th><th>code</th><th>username</th><th>email</th><th>sig ok</th></tr>
 {rows or "<tr><td colspan=7>no requests yet</td></tr>"}
</table>
<script>setTimeout(() => location.replace('/_control/'), 3000)</script>
"""

    def wait_for(self, n: int, timeout: float = 10.0) -> bool:
        """Block until at least *n* requests have arrived."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.request_count >= n:
                return True
            time.sleep(0.05)
        return self.request_count >= n

    # ── request handling ─────────────────────────────────────────────
    def _extract(self, query, body, name):
        if not name:
            return None
        if body is not None and name in body:
            return str(body[name])
        values = query.get(name)
        return values[0] if values else None

    def _verify_signature(self, method, path, headers, code, username, email):
        if not self._hmac_secret:
            return None, ""
        supplied = headers.get("X-Wizarr-Signature", "")
        timestamp = headers.get("X-Wizarr-Timestamp", "")
        nonce = headers.get("X-Wizarr-Nonce", "")
        if not supplied or not timestamp or not nonce:
            return False, "missing signature headers"
        try:
            skew = abs(time.time() - float(timestamp))
        except ValueError:
            return False, "unparseable timestamp"
        if skew > self._skew:
            return False, f"timestamp skew {skew:.0f}s"
        canonical = build_canonical_string(
            timestamp=timestamp,
            nonce=nonce,
            method=method,
            path=path,
            code=code or "",
            username=username or "",
            email=email or "",
        )
        expected = f"sha256={sign(self._hmac_secret, canonical)}"
        if not hmac.compare_digest(supplied, expected):
            return False, "signature mismatch"
        return True, ""

    def _record_and_decide(self, method, path, query, headers, body) -> int:
        with self._lock:
            delay = self._delay
        if path == "/slow" and delay:
            time.sleep(delay)

        code = self._extract(query, body, self._code_param)
        username = self._extract(query, body, self._username_param)
        email = self._extract(query, body, self._email_param)
        sig_valid, sig_error = self._verify_signature(
            method, path, headers, code, username, email
        )

        with self._lock:
            self._requests.append(
                RecordedRequest(
                    method=method,
                    path=path,
                    query=query,
                    headers=headers,
                    body=body,
                    signature_valid=sig_valid,
                    signature_error=sig_error,
                    received_at=time.time(),
                    code=code,
                    username=username,
                    email=email,
                )
            )

            if path == "/boom":
                return 500
            if path == "/redirect":
                return 302
            if path == "/teapot":
                return 418

            if sig_valid is False:
                return 401
            if self._auth_header and not hmac.compare_digest(
                headers.get(self._auth_header, ""), self._auth_value or ""
            ):
                return 401

            for expected, actual in (
                (self._expect_code, code),
                (self._expect_username, username),
                (self._expect_email, email),
            ):
                if expected is not None and actual != expected:
                    return self._fail_status

            if self._programmed:
                return (
                    self._programmed.pop(0)
                    if len(self._programmed) > 1
                    else self._programmed[0]
                )
            return self._status
