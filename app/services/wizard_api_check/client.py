"""Outbound HTTP for the wizard API-check gate.

The endpoint is admin-configured but the *result* is shown to an unauthenticated
invited user, so this layer is deliberately one-way: it reports whether the
upstream answered with an expected status and nothing else. The response body is
never read, redirects are never followed, and errors are collapsed to a coarse
reason so the user cannot learn anything about the admin's network.
"""

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests

from app.services.wizard_api_check.config import ALLOWED_SCHEMES, ApiCheckConfig

SIGNATURE_VERSION = "v1"
MAX_CONNECT_TIMEOUT = 5


@dataclass(frozen=True)
class CheckOutcome:
    """Verdict for one upstream call. Deliberately carries no response content."""

    passed: bool
    reason: str  # ok | status | timeout | network | config | redirect
    status_code: int | None = None


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
    """Return the string signed by ``X-Wizarr-Signature``.

    The upstream rebuilds this from the request it received and compares HMACs.
    It must also reject stale timestamps and replayed nonces - Wizarr cannot
    enforce freshness on the upstream's behalf.
    """
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


def _safe_url(url: str) -> str | None:
    """Re-validate the stored URL at call time; the column is not trusted."""
    if not url or any(ch.isspace() for ch in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.hostname:
        return None
    if parts.username or parts.password or "@" in parts.netloc:
        return None
    return url


def _payload(
    cfg: ApiCheckConfig, code: str, username: str, email: str
) -> dict[str, str]:
    fields = (
        (cfg.code_param, code),
        (cfg.username_param, username),
        (cfg.email_param, email),
    )
    return {name: value for name, value in fields if name}


def _headers(
    cfg: ApiCheckConfig, path: str, code: str, username: str, email: str
) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    key = cfg.api_key()

    if cfg.auth_header and key:
        headers[cfg.auth_header] = f"{cfg.auth_prefix}{key}"

    if cfg.sign_requests and key:
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        canonical = build_canonical_string(
            timestamp=timestamp,
            nonce=nonce,
            method=cfg.method,
            path=path,
            code=code,
            username=username,
            email=email,
        )
        digest = hmac.new(key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        headers["X-Wizarr-Timestamp"] = timestamp
        headers["X-Wizarr-Nonce"] = nonce
        headers["X-Wizarr-Signature"] = f"sha256={digest}"

    return headers


def _log_target(url: str) -> str:
    """A URL safe to log: origin plus path, no query string, no credentials."""
    parts = urlsplit(url)
    port = f":{parts.port}" if parts.port else ""
    target = f"{parts.scheme}://{parts.hostname}{port}{parts.path}"
    return target.replace("\r", "").replace("\n", "")


def run_check(
    cfg: ApiCheckConfig, *, code: str, username: str = "", email: str = ""
) -> CheckOutcome:
    """Call the configured endpoint once and report whether it approved."""
    url = _safe_url(cfg.url)
    if url is None:
        logging.warning("Wizard api_check skipped: unusable URL in step configuration")
        return CheckOutcome(passed=False, reason="config")

    path = urlsplit(url).path or "/"
    payload = _payload(cfg, code, username, email)
    headers = _headers(cfg, path, code, username, email)
    timeout = (min(cfg.timeout_seconds, MAX_CONNECT_TIMEOUT), cfg.timeout_seconds)

    kwargs = {"json": payload} if cfg.method == "POST" else {"params": payload}

    try:
        with requests.request(
            cfg.method,
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
            **kwargs,
        ) as response:
            status = response.status_code
    except requests.exceptions.Timeout:
        logging.warning("Wizard api_check timed out: %s", _log_target(url))
        return CheckOutcome(passed=False, reason="timeout")
    except requests.exceptions.RequestException as exc:
        logging.warning(
            "Wizard api_check failed: %s (%s)", _log_target(url), type(exc).__name__
        )
        return CheckOutcome(passed=False, reason="network")

    if status in cfg.expect_status:
        return CheckOutcome(passed=True, reason="ok", status_code=status)
    if 300 <= status < 400:
        # Never chase a redirect: it would replay the auth header at a host the
        # admin did not configure.
        logging.warning(
            "Wizard api_check upstream redirected (%s); not following", status
        )
        return CheckOutcome(passed=False, reason="redirect", status_code=status)
    return CheckOutcome(passed=False, reason="status", status_code=status)
