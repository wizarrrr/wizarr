"""Show password button on the public password forms (wizarrrr/wizarr#1342)."""

import re

import pytest
from flask import render_template

from app.forms.join import JoinForm
from app.forms.setup import AdminAccountForm

TOGGLE = re.compile(
    r'<button type="button"\s+data-password-toggle\s+'
    r'aria-controls="(?P<field>[^"]+)"\s+'
    r'aria-pressed="false"\s+'
    r'aria-label="Show password"'
)


@pytest.mark.parametrize(
    ("template", "make_context", "field_ids"),
    [
        (
            "welcome-jellyfin.html",
            lambda: {"form": JoinForm(), "server_type": "jellyfin"},
            ["password", "confirm_password"],
        ),
        (
            "hybrid-password-form.html",
            lambda: {"form": JoinForm(), "code": "ABC123"},
            ["password", "confirm_password"],
        ),
        (
            "choose-password.html",
            lambda: {"code": "ABC123"},
            ["password", "confirm"],
        ),
        (
            "password-reset-form.html",
            lambda: {"code": "ABC123", "username": "alice"},
            ["new_password", "confirm_password"],
        ),
        (
            "setup/admin_account.html",
            lambda: {"form": AdminAccountForm()},
            ["password", "confirm"],
        ),
    ],
)
def test_each_password_field_has_a_toggle(app, template, make_context, field_ids):
    with app.test_request_context("/"):
        html = render_template(template, **make_context())

    assert TOGGLE.findall(html) == field_ids
    for field_id in field_ids:
        field = re.search(rf'<input[^>]*\bid="{field_id}"[^>]*>', html)
        assert field is not None
        assert 'type="password"' in field.group(0)
    assert "js/password-toggle.js" in html
