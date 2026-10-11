from app.forms.join import JoinForm
from app.forms.setup import AdminAccountForm
from app.forms.validators import USERNAME_ALLOWED_CHARS_MESSAGE


def _join_form_payload(**overrides):
    base = {
        "username": "validuser",
        "email": "user@example.com",
        "password": "ValidPass1",
        "confirm_password": "ValidPass1",
        "code": "ABCDEF",
    }
    base.update(overrides)
    return base


def _admin_form_payload(**overrides):
    base = {
        "username": "adminuser",
        "password": "ValidPass1",
        "confirm": "ValidPass1",
    }
    base.update(overrides)
    return base


def test_join_form_rejects_spaces_in_username(app):
    with app.test_request_context(
        method="POST", data=_join_form_payload(username="invalid user")
    ):
        form = JoinForm()

        assert not form.validate()
        assert USERNAME_ALLOWED_CHARS_MESSAGE in form.username.errors


def test_join_form_strips_trailing_whitespace(app):
    with app.test_request_context(
        method="POST", data=_join_form_payload(username="validuser ")
    ):
        form = JoinForm()

        assert form.validate()
        assert form.username.data == "validuser"


def test_join_form_rejects_invalid_symbols(app):
    with app.test_request_context(
        method="POST", data=_join_form_payload(username="bad$user")
    ):
        form = JoinForm()

        assert not form.validate()
        assert USERNAME_ALLOWED_CHARS_MESSAGE in form.username.errors


def test_admin_account_form_strips_username_whitespace(app):
    with app.test_request_context(
        method="POST", data=_admin_form_payload(username=" adminuser ")
    ):
        form = AdminAccountForm()

        assert form.validate()
        assert form.username.data == "adminuser"


def test_admin_account_form_rejects_invalid_username(app):
    with app.test_request_context(
        method="POST", data=_admin_form_payload(username="admin user")
    ):
        form = AdminAccountForm()

        assert not form.validate()
        assert USERNAME_ALLOWED_CHARS_MESSAGE in form.username.errors
