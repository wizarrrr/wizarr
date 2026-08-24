"""The /wizard/api-check/<step_id> poll endpoint.

This is the only unauthenticated, outbound-calling endpoint in the app, so most
of these tests are about what it refuses to do: call the upstream for someone
who is not in the flow, call it twice inside the cooldown, redirect an HTMX
fragment, or leak anything about the upstream's answer.
"""

from tests.external.api_check.conftest import INVITE_CODE, api_check_blob


def url(step_id):
    return f"/wizard/api-check/{step_id}"


def htmx(client, step_id):
    return client.get(url(step_id), headers={"HX-Request": "true"})


class TestAccessControl:
    def test_requires_an_accepted_invitation(self, client, gated_step, mock_api):
        response = htmx(client, gated_step)

        assert response.status_code == 286
        assert mock_api.request_count == 0, "no session must never reach the upstream"

    def test_never_redirects_an_htmx_fragment(self, client, gated_step):
        """A 302 would swap the homepage into the card."""
        response = htmx(client, gated_step)

        assert response.status_code not in {301, 302, 303, 307, 308}
        assert "Location" not in response.headers

    def test_a_pre_invite_session_is_not_enough(self, client, gated_step, mock_api):
        with client.session_transaction() as sess:
            sess["wizarr_invite_code"] = INVITE_CODE
            sess["invitation_in_progress"] = True

        response = htmx(client, gated_step)

        assert response.status_code == 286
        assert mock_api.request_count == 0

    def test_accepted_invitation_is_allowed(
        self, accepted_client, gated_step, mock_api
    ):
        response = htmx(accepted_client, gated_step)

        assert response.status_code in {200, 286}
        assert mock_api.request_count == 1


class TestStepResolution:
    def test_unknown_step_id_makes_no_upstream_call(
        self, accepted_client, gated_step, mock_api
    ):
        response = htmx(accepted_client, 999999)

        assert response.status_code == 286
        assert mock_api.request_count == 0

    def test_ungated_step_makes_no_upstream_call(
        self, accepted_client, make_step, mock_api
    ):
        plain = make_step(1, api_check=None)

        response = htmx(accepted_client, plain)

        assert response.status_code == 286
        assert mock_api.request_count == 0

    def test_pre_invite_step_cannot_be_checked(
        self, accepted_client, make_step, mock_api
    ):
        step_id = make_step(
            0, api_check=api_check_blob(mock_api.path("/check")), category="pre_invite"
        )

        response = htmx(accepted_client, step_id)

        assert response.status_code == 286
        assert mock_api.request_count == 0

    def test_a_step_outside_the_current_flow_is_refused(
        self, accepted_client, make_step, mock_api, app
    ):
        """A forged id from another server's wizard must not trigger a call."""
        from app.extensions import db
        from app.models import WizardStep

        with app.app_context():
            foreign = WizardStep(
                server_type="plex",
                category="post_invite",
                position=0,
                title="Foreign",
                markdown="# x",
                api_check=api_check_blob(mock_api.path("/check")),
            )
            db.session.add(foreign)
            db.session.commit()
            foreign_id = foreign.id

        response = htmx(accepted_client, foreign_id)

        assert response.status_code == 286
        assert mock_api.request_count == 0


class TestVerdicts:
    def test_passing_check_reports_passed(self, accepted_client, gated_step, mock_api):
        response = htmx(accepted_client, gated_step)

        assert response.headers["X-Wizarr-Gate"] == "passed"
        assert response.status_code == 286

    def test_passing_check_triggers_the_unlock_event(self, accepted_client, gated_step):
        response = htmx(accepted_client, gated_step)

        assert "wizard:gate-passed" in response.headers.get("HX-Trigger", "")

    def test_failing_check_reports_pending_and_keeps_polling(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)

        response = htmx(accepted_client, gated_step)

        assert response.status_code == 200
        assert response.headers["X-Wizarr-Gate"] == "pending"
        assert b"hx-trigger" in response.data.lower()

    def test_a_pass_is_remembered_without_calling_upstream_again(
        self, accepted_client, gated_step, mock_api
    ):
        htmx(accepted_client, gated_step)
        assert mock_api.request_count == 1

        response = htmx(accepted_client, gated_step)

        assert response.headers["X-Wizarr-Gate"] == "passed"
        assert mock_api.request_count == 1, "an already-passed gate must not re-call"

    def test_identity_is_sent_to_the_upstream(
        self, accepted_client, gated_step, mock_api
    ):
        from tests.external.api_check.conftest import EMAIL, USERNAME

        htmx(accepted_client, gated_step)

        recorded = mock_api.last()
        assert recorded.code == INVITE_CODE
        assert recorded.username == USERNAME
        assert recorded.email == EMAIL


class TestCooldown:
    def test_second_check_inside_the_interval_is_refused(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)

        htmx(accepted_client, gated_step)
        response = htmx(accepted_client, gated_step)

        assert response.headers["X-Wizarr-Gate"] == "cooldown"
        assert mock_api.request_count == 1, "the cooldown must be enforced server-side"

    def test_cooldown_advertises_retry_after(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)
        htmx(accepted_client, gated_step)

        response = htmx(accepted_client, gated_step)

        assert int(response.headers["Retry-After"]) > 0

    def test_cooldown_still_swaps_a_card(self, accepted_client, gated_step, mock_api):
        mock_api.set_status(403)
        htmx(accepted_client, gated_step)

        response = htmx(accepted_client, gated_step)

        assert response.status_code == 200
        assert b"wizard-api-check" in response.data

    def test_rapid_fire_rechecks_hit_the_upstream_once(
        self, accepted_client, gated_step, mock_api
    ):
        mock_api.set_status(403)

        for _ in range(6):
            htmx(accepted_client, gated_step)

        assert mock_api.request_count == 1


class TestNoInformationLeak:
    def test_upstream_body_is_never_echoed(self, accepted_client, gated_step, mock_api):
        mock_api.set_status(403)

        response = htmx(accepted_client, gated_step)

        assert b'"ok"' not in response.data

    def test_upstream_url_is_never_exposed(self, accepted_client, make_step, mock_api):
        step_id = make_step(
            0, api_check=api_check_blob(mock_api.path("/private-internal-path"))
        )
        mock_api.set_status(403)

        response = htmx(accepted_client, step_id)

        assert b"private-internal-path" not in response.data
        assert str(mock_api.port).encode() not in response.data

    def test_failure_reasons_are_indistinguishable_to_the_user(
        self, accepted_client, make_step, app
    ):
        """DNS failure and a 500 must look the same from the browser."""
        import socket

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            dead_port = sock.getsockname()[1]

        refused = make_step(
            0, api_check=api_check_blob(f"http://127.0.0.1:{dead_port}/c")
        )
        dns = make_step(1, api_check=api_check_blob("http://wizarr-nope.invalid/c"))

        first = htmx(accepted_client, refused)
        second = htmx(accepted_client, dns)

        assert (
            first.headers["X-Wizarr-Gate"]
            == second.headers["X-Wizarr-Gate"]
            == "pending"
        )

    def test_api_key_never_appears_in_the_response(
        self, accepted_client, make_step, signed_mock_api, signed_blob_factory
    ):
        from tests.external.api_check.conftest import API_SECRET

        step_id = make_step(
            0, api_check=signed_blob_factory(signed_mock_api.path("/check"))
        )

        response = htmx(accepted_client, step_id)

        assert API_SECRET.encode() not in response.data


class TestAdminAccess:
    def test_admins_may_poll_without_an_invitation(
        self, admin_client, gated_step, mock_api
    ):
        response = htmx(admin_client, gated_step)

        assert response.status_code in {200, 286}
        assert mock_api.request_count == 1
