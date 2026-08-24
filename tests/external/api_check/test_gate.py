"""Session-backed gate state: passes, cooldowns, poll caps and index clamping.

The gate is what makes the check authoritative rather than decorative, so these
tests care most about the ways a determined user might try to get past it:
replaying another invitation's session, hammering the re-check button, or
jumping straight to a later step index.
"""

import time
import types

import pytest

from app.services.wizard_api_check import gate
from app.services.wizard_api_check.config import normalize


def step(step_id, *, active=True, category="post_invite"):
    """A minimal stand-in for the wizard's step adapter."""
    raw = {
        "version": 1,
        "enabled": active,
        "url": "https://api.example.com/check" if active else "",
        "sign_requests": False,
    }
    return types.SimpleNamespace(
        step_id=step_id, api_check=normalize(raw, category=category)
    )


def legacy_step():
    """A markdown-file step: no id, no config."""
    return types.SimpleNamespace(content="# hello")


@pytest.fixture
def ctx(app):
    """A request context with an accepted invitation in the session."""
    with app.test_request_context("/wizard/post-wizard/0") as context:
        from flask import session

        session["wizard_access"] = "INVITE-A"
        gate._IN_PROCESS_CALLS.clear()
        yield context


class TestPassTracking:
    def test_unseen_step_has_not_passed(self, ctx):
        assert gate.has_passed(3) is False

    def test_marking_a_pass_is_remembered(self, ctx):
        gate.mark_passed(3)

        assert gate.has_passed(3) is True

    def test_passes_are_per_step(self, ctx):
        gate.mark_passed(3)

        assert gate.has_passed(4) is False

    def test_marking_twice_is_idempotent(self, ctx):
        from flask import session

        gate.mark_passed(3)
        gate.mark_passed(3)

        assert session[gate.GATE_SESSION_KEY]["passed"] == [3]

    def test_none_step_id_is_ignored(self, ctx):
        gate.mark_passed(None)

        assert gate.has_passed(None) is False


class TestScopeIsolation:
    def test_switching_invitation_discards_earlier_passes(self, ctx):
        from flask import session

        gate.mark_passed(3)
        session["wizard_access"] = "INVITE-B"

        assert gate.has_passed(3) is False

    def test_returning_to_the_original_invitation_does_not_resurrect_passes(self, ctx):
        from flask import session

        gate.mark_passed(3)
        session["wizard_access"] = "INVITE-B"
        gate.has_passed(3)
        session["wizard_access"] = "INVITE-A"

        assert gate.has_passed(3) is False

    def test_scope_is_not_the_raw_invite_code(self, ctx):
        from flask import session

        gate.mark_passed(3)

        assert "INVITE-A" not in str(session[gate.GATE_SESSION_KEY])

    def test_clear_removes_all_state(self, ctx):
        from flask import session

        gate.mark_passed(3)
        gate.clear()

        assert gate.GATE_SESSION_KEY not in session
        assert gate.has_passed(3) is False


class TestCooldown:
    def test_first_call_is_allowed(self, ctx):
        assert gate.reserve(3, interval=10) == 0.0

    def test_second_call_within_the_interval_is_refused(self, ctx):
        gate.reserve(3, interval=10)

        remaining = gate.reserve(3, interval=10)

        assert 0 < remaining <= 10

    def test_cooldown_is_per_step(self, ctx):
        gate.reserve(3, interval=10)

        assert gate.reserve(4, interval=10) == 0.0

    def test_reservation_is_taken_before_the_upstream_call(self, ctx):
        """Two racing requests must not both reach the upstream."""
        allowed = [gate.reserve(3, interval=30) for _ in range(5)]

        assert allowed.count(0.0) == 1

    def test_cooldown_expires(self, ctx):
        gate.reserve(3, interval=10)
        gate._IN_PROCESS_CALLS.clear()
        from flask import session

        session[gate.GATE_SESSION_KEY]["next_at"]["3"] = time.time() - 1

        assert gate.reserve(3, interval=10) == 0.0

    def test_in_process_floor_survives_a_wiped_session_entry(self, ctx):
        """A client cannot shorten the cooldown by dropping the session value."""
        from flask import session

        gate.reserve(3, interval=30)
        session[gate.GATE_SESSION_KEY]["next_at"].clear()

        assert gate.reserve(3, interval=30) > 0


class TestPollCap:
    def test_not_capped_before_the_first_poll(self, ctx):
        assert gate.is_capped(3, max_poll_seconds=600) is False

    def test_not_capped_within_the_window(self, ctx):
        gate.note_poll_started(3)

        assert gate.is_capped(3, max_poll_seconds=600) is False

    def test_capped_after_the_window(self, ctx):
        from flask import session

        gate.note_poll_started(3)
        session[gate.GATE_SESSION_KEY]["started"]["3"] = time.time() - 601

        assert gate.is_capped(3, max_poll_seconds=600) is True

    def test_first_poll_timestamp_is_not_reset_by_later_polls(self, ctx):
        from flask import session

        gate.note_poll_started(3)
        original = session[gate.GATE_SESSION_KEY]["started"]["3"]
        gate.note_poll_started(3)

        assert session[gate.GATE_SESSION_KEY]["started"]["3"] == original


class TestFirstLockedIndex:
    def test_no_steps_are_never_locked(self, ctx):
        assert gate.first_locked_index([], exempt=False) is None

    def test_ungated_steps_are_never_locked(self, ctx):
        steps = [step(1, active=False), step(2, active=False)]

        assert gate.first_locked_index(steps, exempt=False) is None

    def test_returns_the_first_unpassed_gate(self, ctx):
        steps = [step(1, active=False), step(2), step(3)]

        assert gate.first_locked_index(steps, exempt=False) == 1

    def test_passing_the_first_gate_advances_to_the_next(self, ctx):
        steps = [step(1), step(2)]
        gate.mark_passed(1)

        assert gate.first_locked_index(steps, exempt=False) == 1

    def test_all_gates_passed_unlocks_everything(self, ctx):
        steps = [step(1), step(2)]
        gate.mark_passed(1)
        gate.mark_passed(2)

        assert gate.first_locked_index(steps, exempt=False) is None

    def test_admins_are_exempt(self, ctx):
        steps = [step(1)]

        assert gate.first_locked_index(steps, exempt=True) is None

    def test_pre_invite_steps_cannot_gate(self, ctx):
        steps = [step(1, category="pre_invite")]

        assert gate.first_locked_index(steps, exempt=False) is None

    def test_legacy_markdown_steps_are_skipped(self, ctx):
        steps = [legacy_step(), step(2)]

        assert gate.first_locked_index(steps, exempt=False) == 1

    def test_a_step_without_an_id_cannot_gate(self, ctx):
        orphan = types.SimpleNamespace(step_id=None, api_check=step(1).api_check)

        assert gate.first_locked_index([orphan], exempt=False) is None


class TestAnonymousAndAdminScopes:
    def test_no_invitation_still_works_without_crashing(self, app):
        with app.test_request_context("/wizard/post-wizard/0"):
            gate._IN_PROCESS_CALLS.clear()
            gate.mark_passed(3)

            assert gate.has_passed(3) is True

    def test_an_anonymous_pass_does_not_leak_into_an_invitation(self, app):
        with app.test_request_context("/wizard/post-wizard/0"):
            from flask import session

            gate._IN_PROCESS_CALLS.clear()
            gate.mark_passed(3)
            session["wizard_access"] = "INVITE-A"

            assert gate.has_passed(3) is False
