"""Configuration schema for the wizard API-check gate.

The blob lives on ``wizard_step.api_check`` and is authored by an admin, so it
is treated as untrusted on read: :func:`normalize` never raises and clamps every
bound rather than trusting what the column happens to contain.
"""

import logging
import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any
from urllib.parse import urlsplit

VERSION = 1

ALLOWED_METHODS = ("GET", "POST")
ALLOWED_SCHEMES = ("http", "https")
GATED_CATEGORY = "post_invite"

MAX_URL_LEN = 2048
MAX_HEADER_LEN = 64
MAX_PREFIX_LEN = 32
MAX_KEY_LEN = 4096
MAX_PARAM_LEN = 64
MAX_MESSAGE_LEN = 500
MAX_EXPECT_STATUS = 10

MIN_INTERVAL, MAX_INTERVAL = 5, 300
MIN_TIMEOUT, MAX_TIMEOUT = 1, 15
MIN_MAX_POLL, MAX_MAX_POLL = 30, 3600

DEFAULT_INTERVAL = 10
DEFAULT_TIMEOUT = 5
DEFAULT_MAX_POLL = 600
DEFAULT_HEADER = "Authorization"
DEFAULT_PREFIX = "Bearer "
DEFAULT_STATUS = (200,)

_HEADER_RE = re.compile(rf"^[A-Za-z0-9-]{{1,{MAX_HEADER_LEN}}}$")
_PARAM_RE = re.compile(rf"^[A-Za-z0-9_.-]{{1,{MAX_PARAM_LEN}}}$")
_PREFIX_RE = re.compile(r"^[\x20-\x7e]*$")
_TEMPLATE_RE = re.compile(r"\{\{|\{%|\{#|\}\}|%\}|#\}")
_CONTROL_RE = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")


@dataclass(frozen=True)
class ApiCheckConfig:
    """A validated, clamped view of the stored ``api_check`` blob.

    ``category`` is not part of the stored blob – it is carried from the owning
    step so :attr:`is_active` can enforce the post-invite-only rule in one place.
    """

    version: int = VERSION
    enabled: bool = False
    method: str = "GET"
    url: str = ""
    auth_header: str = DEFAULT_HEADER
    auth_prefix: str = DEFAULT_PREFIX
    api_key_enc: str = ""
    code_param: str = "code"
    username_param: str = "username"
    email_param: str = "email"
    expect_status: tuple[int, ...] = DEFAULT_STATUS
    interval_seconds: int = DEFAULT_INTERVAL
    timeout_seconds: int = DEFAULT_TIMEOUT
    max_poll_seconds: int = DEFAULT_MAX_POLL
    sign_requests: bool = True
    pending_message: str = ""
    success_message: str = ""
    category: str = field(default=GATED_CATEGORY, compare=True)

    def __repr__(self) -> str:
        return (
            f"ApiCheckConfig(enabled={self.enabled}, method={self.method!r}, "
            f"url={self.url!r}, category={self.category!r}, key=***)"
        )

    @property
    def is_active(self) -> bool:
        """Whether this gate may block a user.

        Signed gates without a key stay inert so an imported step (which never
        carries a key) cannot lock anyone out.
        """
        return bool(
            self.enabled
            and self.url
            and (not self.sign_requests or self.api_key_enc)
            and self.category == GATED_CATEGORY
        )

    def api_key(self) -> str:
        """Decrypt the stored credential, returning "" if it is unusable."""
        if not self.api_key_enc:
            return ""
        from app.services.ldap.encryption import decrypt_credential

        try:
            return (
                decrypt_credential(self.api_key_enc).replace("\r", "").replace("\n", "")
            )
        except Exception:
            logging.warning("Wizard api_check credential could not be decrypted")
            return ""

    def to_dict(self) -> dict[str, Any]:
        """Return the storable blob (JSON-native, excludes the step category)."""
        blob = asdict(self)
        blob.pop("category", None)
        blob["expect_status"] = list(self.expect_status)
        return blob

    def without_key(self) -> "ApiCheckConfig":
        return replace(self, api_key_enc="")


def _as_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _as_int(value: Any, default: int, low: int, high: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        candidate = value
    elif isinstance(value, str):
        try:
            candidate = int(value.strip())
        except ValueError:
            return default
    else:
        return default
    return max(low, min(candidate, high))


def _as_text(value: Any, default: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str):
        return default
    if value == "":
        return ""
    return value if pattern.match(value) else default


def _clean_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    url = value.strip()
    if not url or len(url) > MAX_URL_LEN:
        return ""
    if any(ch.isspace() for ch in url):
        return ""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.hostname:
        return ""
    if parts.username or parts.password or "@" in parts.netloc:
        return ""
    return url


def _clean_message(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = _CONTROL_RE.sub("", value)[:MAX_MESSAGE_LEN]
    # Fail closed: the render pass neutralises braces too, but a hand-edited
    # column should never reach it carrying template syntax.
    return "" if _TEMPLATE_RE.search(text) else text


def _clean_statuses(value: Any) -> tuple[int, ...]:
    if isinstance(value, bool):
        return DEFAULT_STATUS
    candidates = [value] if isinstance(value, int) else value
    if not isinstance(candidates, list | tuple):
        return DEFAULT_STATUS
    codes = sorted(
        {
            code
            for code in candidates
            if isinstance(code, int)
            and not isinstance(code, bool)
            and 100 <= code <= 599
        }
    )
    return tuple(codes[:MAX_EXPECT_STATUS]) or DEFAULT_STATUS


def normalize(raw: Any, *, category: str = GATED_CATEGORY) -> ApiCheckConfig:
    """Return a validated config for *raw*, never raising.

    Anything unrecognised – a missing column, a wrong type, a future version,
    an out-of-range number – collapses to a safe, disabled default.
    """
    empty = ApiCheckConfig(category=category or "")
    if not isinstance(raw, dict) or raw.get("version") != VERSION:
        return empty

    method = raw.get("method")
    method = method.strip().upper() if isinstance(method, str) else ""

    key = raw.get("api_key_enc")
    key = key if isinstance(key, str) and 0 < len(key) <= MAX_KEY_LEN else ""

    prefix = raw.get("auth_prefix")
    if (
        not isinstance(prefix, str)
        or len(prefix) > MAX_PREFIX_LEN
        or not _PREFIX_RE.match(prefix)
    ):
        prefix = DEFAULT_PREFIX

    return ApiCheckConfig(
        enabled=_as_bool(raw.get("enabled"), False),
        method=method if method in ALLOWED_METHODS else "GET",
        url=_clean_url(raw.get("url")),
        auth_header=_as_text(raw.get("auth_header"), DEFAULT_HEADER, _HEADER_RE),
        auth_prefix=prefix,
        api_key_enc=key,
        code_param=_as_text(raw.get("code_param"), "code", _PARAM_RE),
        username_param=_as_text(raw.get("username_param"), "username", _PARAM_RE),
        email_param=_as_text(raw.get("email_param"), "email", _PARAM_RE),
        expect_status=_clean_statuses(raw.get("expect_status")),
        interval_seconds=_as_int(
            raw.get("interval_seconds"), DEFAULT_INTERVAL, MIN_INTERVAL, MAX_INTERVAL
        ),
        timeout_seconds=_as_int(
            raw.get("timeout_seconds"), DEFAULT_TIMEOUT, MIN_TIMEOUT, MAX_TIMEOUT
        ),
        max_poll_seconds=_as_int(
            raw.get("max_poll_seconds"), DEFAULT_MAX_POLL, MIN_MAX_POLL, MAX_MAX_POLL
        ),
        sign_requests=_as_bool(raw.get("sign_requests"), True),
        pending_message=_clean_message(raw.get("pending_message")),
        success_message=_clean_message(raw.get("success_message")),
        category=category or "",
    )


def public_view(raw: Any, *, category: str = GATED_CATEGORY) -> dict[str, Any]:
    """Return the blob with the credential replaced by a presence flag.

    This is what reaches exports, the widget context and any JSON response –
    the ciphertext itself must never leave the service layer.
    """
    cfg = raw if isinstance(raw, ApiCheckConfig) else normalize(raw, category=category)
    view = cfg.to_dict()
    view.pop("api_key_enc", None)
    view["has_api_key"] = bool(cfg.api_key_enc)
    view["is_active"] = cfg.is_active
    return view


def _parse_expect_status(value: Any) -> list[int]:
    """Parse the admin's free-text comma list, e.g. ``"200, 204"``.

    Unparsable tokens are dropped silently; :func:`normalize` is what enforces
    the valid HTTP status range and supplies the default if nothing survives.
    """
    if not isinstance(value, str):
        return []
    codes = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            codes.append(int(token))
        except ValueError:
            continue
    return codes


def from_form(
    form: Any, *, category: str, existing: dict[str, Any] | None = None
) -> tuple[dict[str, Any] | None, list[str]]:
    """Build the storable ``api_check`` blob from a submitted admin form.

    Unlike :func:`normalize`, this is the authoring boundary: an out-of-range
    number or a rejected URL is refused – with the error attached to the
    offending field – rather than silently clamped, so a typo cannot produce
    a gate that quietly behaves differently than what was entered. ``existing``
    is the step's previously stored blob, consulted only so a blank password
    field preserves the credential already on file instead of erasing it.
    """
    from flask_babel import gettext as _

    existing = existing if isinstance(existing, dict) else {}
    errors: list[str] = []

    def fail(field: Any, message: str) -> None:
        field.errors.append(message)
        errors.append(message)

    enabled = bool(form.api_check_enabled.data)
    if enabled and category != GATED_CATEGORY:
        fail(
            form.api_check_enabled,
            _("The API gate can only be enabled on post-invite steps."),
        )

    url = (form.api_check_url.data or "").strip()
    if url and not _clean_url(url):
        fail(form.api_check_url, _("Enter a valid http:// or https:// URL."))
    elif enabled and not url:
        fail(form.api_check_url, _("A URL is required to enable the API gate."))

    # A signed gate with no key stays inert, so refuse it here rather than let
    # the admin believe the step is gated when it is not.
    signing = bool(form.api_check_sign_requests.data)
    has_key = bool(form.api_check_api_key.data) or (
        not form.api_check_clear_key.data and bool(existing.get("api_key_enc"))
    )
    if enabled and signing and not has_key:
        fail(
            form.api_check_api_key,
            _("An API key is required while request signing is enabled."),
        )

    interval = form.api_check_interval_seconds.data
    if interval is not None and not (MIN_INTERVAL <= interval <= MAX_INTERVAL):
        fail(
            form.api_check_interval_seconds,
            _(
                "Interval must be between %(low)s and %(high)s seconds.",
                low=MIN_INTERVAL,
                high=MAX_INTERVAL,
            ),
        )

    timeout = form.api_check_timeout_seconds.data
    if timeout is not None and not (MIN_TIMEOUT <= timeout <= MAX_TIMEOUT):
        fail(
            form.api_check_timeout_seconds,
            _(
                "Timeout must be between %(low)s and %(high)s seconds.",
                low=MIN_TIMEOUT,
                high=MAX_TIMEOUT,
            ),
        )

    max_poll = form.api_check_max_poll_seconds.data
    if max_poll is not None and not (MIN_MAX_POLL <= max_poll <= MAX_MAX_POLL):
        fail(
            form.api_check_max_poll_seconds,
            _(
                "Give up after must be between %(low)s and %(high)s seconds.",
                low=MIN_MAX_POLL,
                high=MAX_MAX_POLL,
            ),
        )

    pending_message = form.api_check_pending_message.data or ""
    if _TEMPLATE_RE.search(pending_message):
        fail(
            form.api_check_pending_message,
            _("Messages cannot contain template syntax ({{, {%, or {#)."),
        )

    success_message = form.api_check_success_message.data or ""
    if _TEMPLATE_RE.search(success_message):
        fail(
            form.api_check_success_message,
            _("Messages cannot contain template syntax ({{, {%, or {#)."),
        )

    if errors:
        return None, errors

    if form.api_check_clear_key.data:
        api_key_enc = ""
    else:
        from app.services.ldap.encryption import encrypt_credential

        new_key = form.api_check_api_key.data or ""
        api_key_enc = (
            encrypt_credential(new_key) if new_key else existing.get("api_key_enc", "")
        )

    raw = {
        "version": VERSION,
        "enabled": enabled,
        "method": form.api_check_method.data,
        "url": url,
        "auth_header": form.api_check_auth_header.data or "",
        "auth_prefix": form.api_check_auth_prefix.data or "",
        "api_key_enc": api_key_enc,
        "code_param": form.api_check_code_param.data or "",
        "username_param": form.api_check_username_param.data or "",
        "email_param": form.api_check_email_param.data or "",
        "expect_status": _parse_expect_status(form.api_check_expect_status.data),
        "interval_seconds": interval,
        "timeout_seconds": timeout,
        "max_poll_seconds": max_poll,
        "sign_requests": signing,
        "pending_message": pending_message,
        "success_message": success_message,
    }

    return normalize(raw, category=category).to_dict(), []


def to_form(cfg: ApiCheckConfig) -> dict[str, Any]:
    """Values to prefill the edit form. The credential itself never appears.

    ``has_api_key`` is not a form field – it tells the template whether to
    show a "key on file" indicator next to the (always-blank) password field.
    """
    return {
        "api_check_enabled": cfg.enabled,
        "api_check_method": cfg.method,
        "api_check_url": cfg.url,
        "api_check_auth_header": cfg.auth_header,
        "api_check_auth_prefix": cfg.auth_prefix,
        "api_check_code_param": cfg.code_param,
        "api_check_username_param": cfg.username_param,
        "api_check_email_param": cfg.email_param,
        "api_check_expect_status": ", ".join(str(code) for code in cfg.expect_status),
        "api_check_interval_seconds": cfg.interval_seconds,
        "api_check_timeout_seconds": cfg.timeout_seconds,
        "api_check_max_poll_seconds": cfg.max_poll_seconds,
        "api_check_sign_requests": cfg.sign_requests,
        "api_check_pending_message": cfg.pending_message,
        "api_check_success_message": cfg.success_message,
        "has_api_key": bool(cfg.api_key_enc),
    }
