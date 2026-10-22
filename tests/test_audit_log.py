"""Every change to a person's account leaves one line in the audit log.

Wizarr logs at WARNING, so a join, a delete, a disable, an expiry or a user
sync wrote nothing and there was no way to tell afterwards what had happened to
an account. The audit logger writes one INFO line per change on its own handler.
"""

import datetime
import logging

import pytest

from app.extensions import db
from app.models import Invitation, MediaServer, User
from app.services import audit


@pytest.fixture
def lines(caplog):
    # The audit logger doesn't propagate, so attach the capture handler to it
    audit._server_names.clear()
    audit.audit_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="wizarr.audit")
    yield lambda: [r.getMessage() for r in caplog.records if r.name == "wizarr.audit"]
    audit.audit_logger.removeHandler(caplog.handler)


@pytest.fixture
def server(session):
    row = MediaServer(
        name="Books", server_type="audiobookshelf", url="http://x", api_key="k"
    )
    session.add(row)
    session.commit()
    return row


def _user(session, server, **extra):
    user = User(
        token="t",
        username="sam",
        email="sam@example.com",
        code=extra.pop("code", "INVITE0001"),
        server_id=server.id,
        **extra,
    )
    session.add(user)
    session.commit()
    return user


def test_audit_logger_has_its_own_info_handler_whatever_the_log_level():
    from typing import Any, cast

    from app.logging_config import LOGGING_CONFIG

    config = cast("dict[str, Any]", LOGGING_CONFIG)
    logger = config["loggers"]["wizarr.audit"]
    assert logger["level"] == "INFO"
    assert logger["propagate"] is False
    assert config["handlers"][logger["handlers"][0]]["level"] == "INFO"


def test_a_join_is_logged_with_its_invite(session, server, lines, monkeypatch):
    monkeypatch.setattr(
        audit, "has_request_context", lambda: False
    )  # the scheduler or a script
    _user(session, server)

    (line,) = [x for x in lines() if "user_added" in x]
    assert "source=invite" in line
    assert "server=Books" in line
    assert "email=sam@example.com" in line
    assert "code=INVITE0001" in line
    assert "actor=system" in line


def test_an_account_the_sync_imports_says_so(session, server, lines):
    _user(session, server, code="empty")

    (line,) = [x for x in lines() if "user_added" in x]
    assert "source=sync" in line


def test_a_delete_is_logged(session, server, lines):
    user = _user(session, server)
    db.session.delete(user)
    db.session.commit()

    (line,) = [x for x in lines() if "user_removed" in x]
    assert "username=sam" in line
    assert "server=Books" in line


def test_a_disable_and_a_new_expiry_are_logged(session, server, lines):
    user = _user(session, server)
    user.is_disabled = True
    user.expires = datetime.datetime(2026, 11, 1, 6, 0, tzinfo=datetime.UTC)
    db.session.commit()

    changed = [x for x in lines() if "user_changed" in x]
    assert any("field=is_disabled" in x and "new=True" in x for x in changed)
    assert any(
        "field=expires" in x and "new=" in x and "2026-11-01" in x for x in changed
    )


def test_a_rename_or_a_note_is_not_logged(session, server, lines):
    user = _user(session, server)
    user.notes = "hello"
    user.username = "samuel"
    db.session.commit()

    assert [x for x in lines() if "user_changed" in x] == []


def test_an_invite_is_logged_when_made_and_when_deleted(session, lines):
    invitation = Invitation(code="AUDITINV01")
    session.add(invitation)
    session.commit()
    db.session.delete(invitation)
    db.session.commit()

    out = lines()
    assert any("invite_created" in x and "code=AUDITINV01" in x for x in out)
    assert any("invite_deleted" in x and "code=AUDITINV01" in x for x in out)


def test_the_actor_is_the_admin_then_the_access_email_then_invitee(app, monkeypatch):
    from types import SimpleNamespace

    from app.services import cloudflare_access

    with app.test_request_context():
        monkeypatch.setattr(
            audit,
            "current_user",
            SimpleNamespace(is_authenticated=True, username="alex"),
        )
        assert audit.actor() == "alex"

        monkeypatch.setattr(
            audit, "current_user", SimpleNamespace(is_authenticated=False)
        )
        monkeypatch.setattr(cloudflare_access, "enabled", lambda: True)
        monkeypatch.setattr(
            cloudflare_access, "verified_claims", lambda: {"email": "rob@example.com"}
        )
        assert audit.actor() == "rob@example.com"

        monkeypatch.setattr(cloudflare_access, "verified_claims", lambda: None)
        assert audit.actor() == "invitee"


def test_outside_a_request_the_actor_is_the_system(monkeypatch):
    monkeypatch.setattr(audit, "has_request_context", lambda: False)
    assert audit.actor() == "system"


def test_remote_calls_about_an_account_are_logged(session, server, lines, monkeypatch):
    from unittest.mock import Mock

    from app.services.media import service

    client = Mock()
    client.enable_user.return_value = True
    client.disable_user.return_value = False
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _s: client)
    user = _user(session, server)

    service.enable_user(user.id)
    service.disable_user(user.id)
    service.delete_user(user.id)

    out = lines()
    assert any("remote_enable" in x and "ok=True" in x for x in out)
    assert any("remote_disable" in x and "ok=False" in x for x in out)
    assert any(
        "remote_delete" in x and "ok=True" in x and "server=Books" in x for x in out
    )


def test_a_failed_remote_delete_is_logged_with_the_error(
    session, server, lines, monkeypatch
):
    from unittest.mock import Mock

    from app.services.media import service

    client = Mock()
    client.delete_user.side_effect = RuntimeError("server down")
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _s: client)
    user = _user(session, server)

    service.delete_user(user.id)

    assert any(
        "remote_delete" in x and "ok=False" in x and "server down" in x for x in lines()
    )


def test_reading_the_actor_does_not_cache_an_anonymous_user(app):
    """Flask-Login keeps the user on g, so an audit line written before anyone
    signed in must not leave "anonymous" behind for the rest of the request."""
    from flask import g

    from app.services.audit import actor

    with app.test_request_context("/"):
        assert actor() == "invitee"
        assert "_login_user" not in g
