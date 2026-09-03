"""Schema tests for the wizard API-check configuration blob.

The config is admin-authored and stored as JSON on ``wizard_step.api_check``.
``normalize`` is the only read path, so it must never raise no matter what the
column contains, and it must clamp every bound rather than trusting the blob.
"""

import pytest

from app.services.wizard_api_check.config import (
    DEFAULT_INTERVAL,
    DEFAULT_MAX_POLL,
    DEFAULT_TIMEOUT,
    MAX_EXPECT_STATUS,
    MAX_INTERVAL,
    MAX_MAX_POLL,
    MAX_MESSAGE_LEN,
    MAX_TIMEOUT,
    MAX_URL_LEN,
    MIN_INTERVAL,
    MIN_MAX_POLL,
    MIN_TIMEOUT,
    ApiCheckConfig,
    normalize,
    public_view,
)


def cfg(**overrides):
    """Build a normalized config from a valid enabled baseline."""
    raw = {
        "version": 1,
        "enabled": True,
        "method": "GET",
        "url": "https://api.example.com/check",
        "api_key_enc": "ciphertext",
        "sign_requests": True,
    }
    category = overrides.pop("category", "post_invite")
    raw.update(overrides)
    return normalize(raw, category=category)


class TestNormalizeNeverRaises:
    @pytest.mark.parametrize(
        "raw",
        [None, {}, "garbage", [1, 2], 5, True, 3.4, {"version": 99}, {"version": "x"}],
    )
    def test_junk_collapses_to_disabled_default(self, raw):
        result = normalize(raw)

        assert isinstance(result, ApiCheckConfig)
        assert result.enabled is False
        assert result.is_active is False

    def test_wrong_typed_scalars_reset_to_defaults(self):
        result = normalize(
            {
                "version": 1,
                "enabled": "yes",
                "method": ["GET"],
                "url": 12345,
                "interval_seconds": "soon",
                "expect_status": "200",
                "pending_message": 7,
            }
        )

        assert result.method == "GET"
        assert result.url == ""
        assert result.interval_seconds == DEFAULT_INTERVAL
        assert result.expect_status == (200,)
        assert result.pending_message == ""


class TestDefaults:
    def test_empty_blob_defaults(self):
        result = normalize({})

        assert result.version == 1
        assert result.enabled is False
        assert result.method == "GET"
        assert result.url == ""
        assert result.auth_header == "Authorization"
        assert result.auth_prefix == "Bearer "
        assert result.api_key_enc == ""
        assert result.code_param == "code"
        assert result.username_param == "username"
        assert result.email_param == "email"
        assert result.expect_status == (200,)
        assert result.interval_seconds == DEFAULT_INTERVAL
        assert result.timeout_seconds == DEFAULT_TIMEOUT
        assert result.max_poll_seconds == DEFAULT_MAX_POLL
        assert result.sign_requests is True
        assert result.pending_message == ""
        assert result.success_message == ""


class TestMethod:
    @pytest.mark.parametrize(
        ("given", "expected"), [("get", "GET"), ("post", "POST"), ("POST", "POST")]
    )
    def test_case_insensitive(self, given, expected):
        assert cfg(method=given).method == expected

    @pytest.mark.parametrize("given", ["PUT", "DELETE", "TRACE", "", "GET POST"])
    def test_unsupported_method_falls_back_to_get(self, given):
        assert cfg(method=given).method == "GET"


class TestUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.example.com/check",
            "http://127.0.0.1:8080/pwa/status",
            "http://nas.local/api",
        ],
    )
    def test_accepts_http_and_https(self, url):
        assert cfg(url=url).url == url

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://evil.test/",
            "ftp://example.com/x",
            "//evil.com/path",
            "javascript:alert(1)",
            "data:text/plain,hi",
            "example.com/no-scheme",
            "https://",
            "http:///nohost",
        ],
    )
    def test_rejects_non_http_scheme_or_missing_host(self, url):
        result = cfg(url=url)

        assert result.url == ""
        assert result.is_active is False

    @pytest.mark.parametrize(
        "url",
        ["https://user:pass@example.com/x", "http://admin@example.com/x"],
    )
    def test_rejects_embedded_credentials(self, url):
        assert cfg(url=url).url == ""

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/a\r\nX-Evil: 1",
            "https://example.com/a\nb",
            "https://exa mple.com/a",
            "https://example.com/\tx",
        ],
    )
    def test_rejects_whitespace_and_crlf(self, url):
        assert cfg(url=url).url == ""

    def test_rejects_over_length_url(self):
        too_long = "https://example.com/" + ("a" * MAX_URL_LEN)

        assert cfg(url=too_long).url == ""

    def test_surrounding_whitespace_is_trimmed(self):
        assert cfg(url="  https://example.com/x  ").url == "https://example.com/x"


class TestHeaderAndPrefix:
    @pytest.mark.parametrize("header", ["Authorization", "X-API-Key", "x-api-key", "A"])
    def test_accepts_token_charset(self, header):
        assert cfg(auth_header=header).auth_header == header

    def test_empty_header_means_send_none(self):
        assert cfg(auth_header="").auth_header == ""

    @pytest.mark.parametrize(
        "header",
        ["X-Evil\r\nInjected: 1", "has space", "colon:name", "a" * 65, "naïve"],
    )
    def test_rejects_header_injection_charset(self, header):
        assert cfg(auth_header=header).auth_header == "Authorization"

    @pytest.mark.parametrize("prefix", ["Bearer ", "", "Token "])
    def test_accepts_printable_prefix(self, prefix):
        assert cfg(auth_prefix=prefix).auth_prefix == prefix

    @pytest.mark.parametrize("prefix", ["Bearer\r\n", "a" * 33, "tab\there"])
    def test_rejects_bad_prefix(self, prefix):
        assert cfg(auth_prefix=prefix).auth_prefix == "Bearer "


class TestParamNames:
    @pytest.mark.parametrize("field", ["code_param", "username_param", "email_param"])
    def test_empty_means_omit(self, field):
        assert getattr(cfg(**{field: ""}), field) == ""

    @pytest.mark.parametrize("field", ["code_param", "username_param", "email_param"])
    @pytest.mark.parametrize("value", ["invite_code", "user.name", "a-b", "X1"])
    def test_accepts_safe_charset(self, field, value):
        assert getattr(cfg(**{field: value}), field) == value

    @pytest.mark.parametrize("field", ["code_param", "username_param", "email_param"])
    @pytest.mark.parametrize("value", ["has space", "a=b", "a&b[]", "a" * 65, "eq="])
    def test_rejects_unsafe_charset(self, field, value):
        defaults = {
            "code_param": "code",
            "username_param": "username",
            "email_param": "email",
        }

        assert getattr(cfg(**{field: value}), field) == defaults[field]


class TestExpectStatus:
    def test_deduped_and_sorted(self):
        assert cfg(expect_status=[204, 200, 204, 201]).expect_status == (200, 201, 204)

    def test_drops_out_of_range_and_non_ints(self):
        assert cfg(expect_status=[200, 99, 600, "abc", None, 204]).expect_status == (
            200,
            204,
        )

    def test_empty_after_filtering_falls_back_to_200(self):
        assert cfg(expect_status=[99, 600]).expect_status == (200,)
        assert cfg(expect_status=[]).expect_status == (200,)

    def test_caps_entry_count(self):
        result = cfg(expect_status=list(range(200, 200 + MAX_EXPECT_STATUS + 5)))

        assert len(result.expect_status) == MAX_EXPECT_STATUS

    def test_accepts_single_int(self):
        assert cfg(expect_status=204).expect_status == (204,)


class TestNumericBounds:
    @pytest.mark.parametrize(
        ("field", "low", "high"),
        [
            ("interval_seconds", MIN_INTERVAL, MAX_INTERVAL),
            ("timeout_seconds", MIN_TIMEOUT, MAX_TIMEOUT),
            ("max_poll_seconds", MIN_MAX_POLL, MAX_MAX_POLL),
        ],
    )
    def test_clamped_to_range(self, field, low, high):
        assert getattr(cfg(**{field: -5}), field) == low
        assert getattr(cfg(**{field: 0}), field) == low
        assert getattr(cfg(**{field: 10**9}), field) == high
        assert getattr(cfg(**{field: low}), field) == low
        assert getattr(cfg(**{field: high}), field) == high

    def test_numeric_strings_are_coerced(self):
        assert cfg(interval_seconds="30").interval_seconds == 30

    def test_bools_are_not_treated_as_numbers(self):
        assert cfg(interval_seconds=True).interval_seconds == DEFAULT_INTERVAL


class TestMessages:
    def test_trimmed_to_max_length(self):
        result = cfg(pending_message="x" * (MAX_MESSAGE_LEN + 50))

        assert len(result.pending_message) == MAX_MESSAGE_LEN

    def test_newlines_survive_control_stripping(self):
        assert cfg(pending_message="a\nb").pending_message == "a\nb"

    def test_control_characters_are_stripped(self):
        assert cfg(pending_message="a\x00\x07b\x7f").pending_message == "ab"

    @pytest.mark.parametrize(
        "message",
        [
            "{{ config.SECRET_KEY }}",
            "{% for x in y %}",
            "{# comment #}",
            "hello {{ 7*7 }} world",
        ],
    )
    def test_template_syntax_is_dropped(self, message):
        assert cfg(pending_message=message).pending_message == ""
        assert cfg(success_message=message).success_message == ""

    def test_unicode_and_emoji_survive(self):
        text = "✅ 完了 🎉 café"

        assert cfg(success_message=text).success_message == text

    def test_html_is_preserved_verbatim_for_the_template_to_escape(self):
        text = "<script>alert(1)</script>"

        assert cfg(pending_message=text).pending_message == text


class TestIsActive:
    def test_fully_configured_signed_gate_is_active(self):
        assert cfg().is_active is True

    def test_disabled_flag_wins(self):
        assert cfg(enabled=False).is_active is False

    def test_blank_url_is_inactive(self):
        assert cfg(url="").is_active is False

    def test_signed_gate_without_key_is_inactive(self):
        assert cfg(api_key_enc="", sign_requests=True).is_active is False

    def test_unsigned_gate_without_key_is_active(self):
        assert cfg(api_key_enc="", sign_requests=False).is_active is True

    @pytest.mark.parametrize("category", ["pre_invite", "", "custom", None])
    def test_only_post_invite_steps_can_gate(self, category):
        assert cfg(category=category).is_active is False

    def test_post_invite_category_is_active(self):
        assert cfg(category="post_invite").is_active is True

    def test_enabled_survives_a_pre_invite_category(self):
        """Category suppresses activation but must not silently erase the config."""
        result = cfg(category="pre_invite")

        assert result.enabled is True
        assert result.url == "https://api.example.com/check"


class TestSerialisation:
    def test_to_dict_round_trips(self):
        original = cfg(
            method="POST",
            expect_status=[201, 204],
            interval_seconds=30,
            pending_message="hold on",
        )

        assert normalize(original.to_dict(), category="post_invite") == original

    def test_to_dict_is_json_native(self):
        blob = cfg(expect_status=[200, 204]).to_dict()

        assert isinstance(blob["expect_status"], list)
        assert blob["expect_status"] == [200, 204]
        assert "category" not in blob

    def test_to_dict_keeps_the_ciphertext_for_storage(self):
        assert cfg(api_key_enc="ciphertext").to_dict()["api_key_enc"] == "ciphertext"


class TestPublicView:
    def test_never_exposes_the_ciphertext(self):
        view = public_view({"version": 1, "enabled": True, "api_key_enc": "ciphertext"})

        assert "api_key_enc" not in view
        assert "ciphertext" not in str(view)

    def test_reports_key_presence_as_a_boolean(self):
        assert (
            public_view({"version": 1, "api_key_enc": "ciphertext"})["has_api_key"]
            is True
        )
        assert public_view({"version": 1, "api_key_enc": ""})["has_api_key"] is False

    def test_handles_a_missing_blob(self):
        view = public_view(None)

        assert view["enabled"] is False
        assert view["has_api_key"] is False

    def test_exposes_the_fields_the_widget_needs(self):
        view = public_view(
            {
                "version": 1,
                "enabled": True,
                "url": "https://example.com/x",
                "interval_seconds": 20,
                "pending_message": "waiting",
            }
        )

        assert view["interval_seconds"] == 20
        assert view["pending_message"] == "waiting"


class TestApiKeyDecryption:
    def test_round_trips_through_the_shared_credential_helpers(self):
        from app.services.ldap.encryption import encrypt_credential

        result = cfg(api_key_enc=encrypt_credential("sk-live-secret"))

        assert result.api_key() == "sk-live-secret"

    def test_undecryptable_ciphertext_yields_empty_string(self):
        assert cfg(api_key_enc="not-a-fernet-token").api_key() == ""

    def test_blank_ciphertext_yields_empty_string(self):
        assert cfg(api_key_enc="", sign_requests=False).api_key() == ""


class TestRepr:
    def test_repr_redacts_the_ciphertext(self):
        text = repr(cfg(api_key_enc="super-secret-ciphertext"))

        assert "super-secret-ciphertext" not in text
        assert "***" in text
