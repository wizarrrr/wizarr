"""Server-side enforcement of the gate across the wizard routes.

Blocking the Next button is cosmetic; these tests cover the part that actually
makes the gate mandatory - that typing a later index, or jumping straight to the
completion page, does not get a user past an unsatisfied check.
"""

from tests.external.api_check.conftest import api_check_blob


def check_url(step_id):
    return f"/wizard/api-check/{step_id}"


class TestIndexClamping:
    def test_a_locked_gate_pins_the_user_to_its_step(
        self, accepted_client, make_step, mock_api
    ):
        make_step(0, api_check=api_check_blob(mock_api.path("/check")))
        make_step(1, api_check=None, markdown="# Second step")
        mock_api.set_status(403)

        response = accepted_client.get(
            "/wizard/post-wizard/1", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "0"

    def test_the_locked_step_reports_itself_as_gated(
        self, accepted_client, gated_step, make_step, mock_api
    ):
        make_step(1, api_check=None, markdown="# Second step")
        mock_api.set_status(403)

        response = accepted_client.get(
            "/wizard/post-wizard/0", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Gate-Locked"] == "true"

    def test_passing_the_gate_releases_the_next_step(
        self, accepted_client, gated_step, make_step, mock_api
    ):
        make_step(1, api_check=None, markdown="# Second step")
        accepted_client.get(check_url(gated_step), headers={"HX-Request": "true"})

        response = accepted_client.get(
            "/wizard/post-wizard/1", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "1"
        assert response.headers["X-Wizard-Gate-Locked"] == "false"

    def test_a_second_gate_clamps_again(self, accepted_client, make_step, mock_api):
        first = make_step(0, api_check=api_check_blob(mock_api.path("/check")))
        make_step(1, api_check=api_check_blob(mock_api.path("/check")))
        make_step(2, api_check=None, markdown="# Third step")

        accepted_client.get(check_url(first), headers={"HX-Request": "true"})
        mock_api.set_status(403)

        response = accepted_client.get(
            "/wizard/post-wizard/2", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "1"

    def test_ungated_wizards_are_unaffected(self, accepted_client, make_step):
        make_step(0, api_check=None, markdown="# One")
        make_step(1, api_check=None, markdown="# Two")

        response = accepted_client.get(
            "/wizard/post-wizard/1", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "1"
        assert response.headers["X-Wizard-Gate-Locked"] == "false"

    def test_an_inactive_gate_does_not_clamp(
        self, accepted_client, make_step, mock_api
    ):
        make_step(
            0,
            api_check=api_check_blob(
                mock_api.path("/check"), sign_requests=True, api_key_enc=""
            ),
        )
        make_step(1, api_check=None, markdown="# Second")

        response = accepted_client.get(
            "/wizard/post-wizard/1", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "1"


class TestCompletionIsGated:
    def test_completion_bounces_back_to_the_locked_step(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)

        response = accepted_client.get("/wizard/complete")

        assert response.status_code in {302, 303}
        assert "/wizard/post-wizard/0" in response.headers["Location"]

    def test_completion_succeeds_once_the_gate_passes(
        self, accepted_client, gated_step, mock_api
    ):
        accepted_client.get(check_url(gated_step), headers={"HX-Request": "true"})

        response = accepted_client.get("/wizard/complete")

        assert "/wizard/post-wizard/" not in response.headers["Location"]

    def test_completion_is_open_when_nothing_is_gated(self, accepted_client, make_step):
        make_step(0, api_check=None, markdown="# One")

        response = accepted_client.get("/wizard/complete")

        assert "/wizard/post-wizard/" not in response.headers["Location"]

    def test_completion_clears_the_gate_state(self, accepted_client, gated_step):
        from app.services.wizard_api_check.gate import GATE_SESSION_KEY

        accepted_client.get(check_url(gated_step), headers={"HX-Request": "true"})
        accepted_client.get("/wizard/complete")

        with accepted_client.session_transaction() as sess:
            assert GATE_SESSION_KEY not in sess


class TestAdminExemption:
    def test_admins_are_not_clamped(
        self, admin_client, gated_step, make_step, mock_api
    ):
        make_step(1, api_check=None, markdown="# Second step")
        mock_api.set_status(403)

        response = admin_client.get(
            f"/wizard/{'jellyfin'}/1", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "1"

    def test_the_preview_route_still_gates_a_non_admin(
        self, accepted_client, gated_step, make_step, mock_api
    ):
        """`phase == preview` must not be usable as a way around the gate."""
        make_step(1, api_check=None, markdown="# Second step")
        mock_api.set_status(403)

        response = accepted_client.get(
            "/wizard/jellyfin/1", headers={"HX-Request": "true"}
        )

        assert response.headers["X-Wizard-Idx"] == "0"


class TestCardRendering:
    def test_the_card_is_rendered_into_the_step(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)

        response = accepted_client.get("/wizard/post-wizard/0")

        assert f'id="wizard-api-check-{gated_step}"'.encode() in response.data

    def test_the_card_is_appended_when_the_admin_forgot_the_placeholder(
        self, accepted_client, make_step, mock_api
    ):
        step_id = make_step(
            0,
            api_check=api_check_blob(mock_api.path("/check")),
            markdown="# No placeholder here",
        )
        mock_api.set_status(403)

        response = accepted_client.get("/wizard/post-wizard/0")

        assert f'id="wizard-api-check-{step_id}"'.encode() in response.data

    def test_the_card_is_not_duplicated_when_the_placeholder_is_present(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)

        response = accepted_client.get("/wizard/post-wizard/0")

        assert response.data.count(f'id="wizard-api-check-{gated_step}"'.encode()) == 1

    def test_no_card_for_an_ungated_step(self, accepted_client, make_step):
        make_step(0, api_check=None, markdown="# Plain\n\n{{ widget:api_check }}")

        response = accepted_client.get("/wizard/post-wizard/0")

        assert b"wizard-api-check" not in response.data


class TestConfigIsNotExposedToStepMarkdown:
    def test_markdown_cannot_print_the_gate_config(
        self, accepted_client, make_step, mock_api
    ):
        """The widget context must stay out of the markdown render context."""
        make_step(
            0,
            api_check=api_check_blob(mock_api.path("/secret-endpoint")),
            markdown="Leak: {{ wizard_api_check }} {{ wizard_step_id }}",
        )
        mock_api.set_status(403)

        response = accepted_client.get("/wizard/post-wizard/0")

        assert b"secret-endpoint" not in response.data
        assert b"interval_seconds" not in response.data


class TestNextButtonIsLocked:
    def test_next_is_disabled_while_the_gate_is_locked(
        self, accepted_client, gated_step, make_step, mock_api
    ):
        make_step(1, api_check=None, markdown="# Second step")
        mock_api.set_status(403)

        response = accepted_client.get("/wizard/post-wizard/0")

        assert b'aria-disabled="true"' in response.data
        assert b'data-disabled="1"' in response.data

    def test_next_is_enabled_once_the_gate_passes(
        self, accepted_client, gated_step, make_step
    ):
        make_step(1, api_check=None, markdown="# Second step")
        accepted_client.get(check_url(gated_step), headers={"HX-Request": "true"})

        response = accepted_client.get("/wizard/post-wizard/0")

        assert b'data-disabled="1"' not in response.data

    def test_an_ungated_step_leaves_next_alone(self, accepted_client, make_step):
        make_step(0, api_check=None, markdown="# One")
        make_step(1, api_check=None, markdown="# Two")

        response = accepted_client.get("/wizard/post-wizard/0")

        assert b'data-disabled="1"' not in response.data

    def test_require_interaction_still_locks_independently(
        self, accepted_client, app, wizard_world
    ):
        from app.extensions import db
        from app.models import WizardStep

        with app.app_context():
            for position in (0, 1):
                db.session.add(
                    WizardStep(
                        server_type="jellyfin",
                        category="post_invite",
                        position=position,
                        title=f"Step {position}",
                        markdown="# Step\n\n[Open](https://example.com)",
                        require_interaction=position == 0,
                    )
                )
            db.session.commit()

        response = accepted_client.get("/wizard/post-wizard/0")

        assert b'data-disabled="1"' in response.data
