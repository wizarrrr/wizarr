"""Admin authoring of the API gate.

Covers the two things an admin can get wrong destructively - losing the stored
credential on an unrelated edit, and attaching a gate to a pre-invite step where
username and email do not exist yet - plus the guarantee that the key is
write-only from the browser's point of view.
"""

from app.extensions import db
from app.models import WizardStep
from app.services.ldap.encryption import encrypt_credential
from app.services.wizard_api_check.config import normalize

SECRET = "sk-live-admin-entered"


def form_payload(**overrides):
    payload = {
        "server_type": "jellyfin",
        "category": "post_invite",
        "title": "Install the app",
        "markdown": "# Install\n\n{{ widget:api_check }}",
        "api_check_enabled": "y",
        "api_check_method": "GET",
        "api_check_url": "https://api.example.com/check",
        "api_check_auth_header": "Authorization",
        "api_check_auth_prefix": "Bearer ",
        "api_check_api_key": SECRET,
        "api_check_code_param": "code",
        "api_check_username_param": "username",
        "api_check_email_param": "email",
        "api_check_expect_status": "200",
        "api_check_interval_seconds": "15",
        "api_check_timeout_seconds": "5",
        "api_check_max_poll_seconds": "600",
        "api_check_sign_requests": "y",
        "api_check_pending_message": "Install the app, then tap Re-check",
        "api_check_success_message": "All set",
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}


def only_step(app):
    with app.app_context():
        return WizardStep.query.order_by(WizardStep.id.desc()).first()


class TestCreate:
    def test_gate_is_saved(self, admin_client, app):
        admin_client.post("/settings/wizard/create", data=form_payload())

        with app.app_context():
            step = only_step(app)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.enabled is True
        assert cfg.url == "https://api.example.com/check"
        assert cfg.interval_seconds == 15
        assert cfg.is_active is True

    def test_api_key_is_encrypted_at_rest(self, admin_client, app):
        admin_client.post("/settings/wizard/create", data=form_payload())

        with app.app_context():
            step = only_step(app)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key_enc != SECRET
        assert SECRET not in str(step.api_check)
        assert cfg.api_key() == SECRET

    def test_expected_statuses_accept_a_comma_list(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create",
            data=form_payload(api_check_expect_status="200, 204"),
        )

        with app.app_context():
            step = only_step(app)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.expect_status == (200, 204)

    def test_a_step_without_the_gate_stores_nothing_active(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create", data=form_payload(api_check_enabled=None)
        )

        with app.app_context():
            step = only_step(app)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.is_active is False


class TestValidation:
    def test_gate_is_refused_on_a_pre_invite_step(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create", data=form_payload(category="pre_invite")
        )

        with app.app_context():
            step = only_step(app)

        assert (
            step is None
            or normalize(step.api_check, category=step.category).enabled is False
        )

    def test_a_non_http_url_is_refused(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create",
            data=form_payload(api_check_url="file:///etc/passwd"),
        )

        with app.app_context():
            step = only_step(app)

        assert (
            step is None or normalize(step.api_check, category=step.category).url == ""
        )

    def test_an_out_of_range_interval_is_refused(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create", data=form_payload(api_check_interval_seconds="1")
        )

        with app.app_context():
            step = only_step(app)

        assert (
            step is None
            or normalize(step.api_check, category=step.category).interval_seconds >= 5
        )

    def test_enabling_without_a_url_is_refused(self, admin_client, app):
        """Otherwise the admin ticks the box and gets a gate that does nothing."""
        admin_client.post(
            "/settings/wizard/create", data=form_payload(api_check_url="")
        )

        with app.app_context():
            step = only_step(app)

        assert (
            step is None
            or normalize(step.api_check, category=step.category).enabled is False
        )

    def test_enabling_a_signed_gate_without_a_key_is_refused(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create", data=form_payload(api_check_api_key="")
        )

        with app.app_context():
            step = only_step(app)

        assert (
            step is None
            or normalize(step.api_check, category=step.category).enabled is False
        )

    def test_the_admin_sees_why_the_save_was_refused(self, admin_client):
        """A refusal the admin cannot see reads as the form silently ignoring them."""
        response = admin_client.post(
            "/settings/wizard/create",
            data=form_payload(api_check_api_key=""),
            headers={"HX-Request": "true"},
        )

        assert b"API key is required" in response.data

    def test_a_bad_url_is_explained_too(self, admin_client):
        response = admin_client.post(
            "/settings/wizard/create",
            data=form_payload(api_check_url="file:///etc/passwd"),
            headers={"HX-Request": "true"},
        )

        assert b"valid http" in response.data

    def test_an_unsigned_gate_needs_no_key(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create",
            data=form_payload(api_check_api_key="", api_check_sign_requests=None),
        )

        with app.app_context():
            step = only_step(app)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.is_active is True

    def test_template_syntax_in_a_message_is_refused(self, admin_client, app):
        admin_client.post(
            "/settings/wizard/create",
            data=form_payload(api_check_pending_message="{{ config.SECRET_KEY }}"),
        )

        with app.app_context():
            step = only_step(app)

        assert (
            step is None
            or normalize(step.api_check, category=step.category).pending_message == ""
        )


class TestEdit:
    def existing(self, app, **blob_overrides):
        blob = {
            "version": 1,
            "enabled": True,
            "method": "GET",
            "url": "https://api.example.com/check",
            "api_key_enc": encrypt_credential(SECRET),
            "sign_requests": True,
            "interval_seconds": 15,
        }
        blob.update(blob_overrides)
        with app.app_context():
            step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                title="Existing",
                markdown="# Existing\n\n{{ widget:api_check }}",
                api_check=blob,
            )
            db.session.add(step)
            db.session.commit()
            return step.id

    def test_a_blank_key_field_preserves_the_stored_credential(self, admin_client, app):
        step_id = self.existing(app)

        admin_client.post(
            f"/settings/wizard/{step_id}/edit",
            data=form_payload(api_check_api_key="", title="Renamed"),
        )

        with app.app_context():
            step = db.session.get(WizardStep, step_id)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key() == SECRET
        assert step.title == "Renamed"

    def test_the_clear_checkbox_wipes_the_credential(self, admin_client, app):
        step_id = self.existing(app)

        admin_client.post(
            f"/settings/wizard/{step_id}/edit",
            data=form_payload(
                api_check_api_key="",
                api_check_clear_key="y",
                api_check_sign_requests=None,
            ),
        )

        with app.app_context():
            step = db.session.get(WizardStep, step_id)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key_enc == ""

    def test_clearing_the_key_of_a_signed_gate_is_refused(self, admin_client, app):
        """Wiping the key while signing stays on would leave an inert gate."""
        step_id = self.existing(app)

        admin_client.post(
            f"/settings/wizard/{step_id}/edit",
            data=form_payload(api_check_api_key="", api_check_clear_key="y"),
        )

        with app.app_context():
            step = db.session.get(WizardStep, step_id)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key() == SECRET

    def test_a_new_key_replaces_the_old_one(self, admin_client, app):
        step_id = self.existing(app)

        admin_client.post(
            f"/settings/wizard/{step_id}/edit",
            data=form_payload(api_check_api_key="sk-live-rotated"),
        )

        with app.app_context():
            step = db.session.get(WizardStep, step_id)
            cfg = normalize(step.api_check, category=step.category)

        assert cfg.api_key() == "sk-live-rotated"

    def test_the_edit_form_never_echoes_the_credential(self, admin_client, app):
        step_id = self.existing(app)

        response = admin_client.get(
            f"/settings/wizard/{step_id}/edit", headers={"HX-Request": "true"}
        )

        assert SECRET.encode() not in response.data

    def test_disabling_the_gate_keeps_the_step(self, admin_client, app):
        step_id = self.existing(app)

        admin_client.post(
            f"/settings/wizard/{step_id}/edit",
            data=form_payload(api_check_enabled=None, api_check_api_key=""),
        )

        with app.app_context():
            step = db.session.get(WizardStep, step_id)
            cfg = normalize(step.api_check, category=step.category)

        assert step is not None
        assert cfg.is_active is False


class TestAdminPreview:
    def test_preview_renders_the_widget_instead_of_raw_syntax(self, admin_client):
        response = admin_client.post(
            "/settings/wizard/preview",
            data={
                "markdown": '# Title\n\n{{ widget:button url="https://x.test" text="Go" }}'
            },
        )

        assert b"widget:button" not in response.data
        assert b"https://x.test" in response.data

    def test_preview_renders_cards(self, admin_client):
        response = admin_client.post(
            "/settings/wizard/preview", data={"markdown": "|||\n# Card\n\nBody\n|||"}
        )

        assert b"card-widget" in response.data

    def test_preview_of_an_api_check_placeholder_is_inert(self, admin_client):
        response = admin_client.post(
            "/settings/wizard/preview", data={"markdown": "{{ widget:api_check }}"}
        )

        assert b"hx-get" not in response.data
