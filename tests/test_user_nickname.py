"""
A user can be given a nickname whether or not they have an Identity.

Identities are only created automatically when two accounts share an
email, so before this fix a user with a single account had no edit button
and no endpoint that could store a nickname for them.
"""

import pytest

from app.extensions import db
from app.models import Identity, MediaServer, User
from app.services.media.service import _auto_link_identities


@pytest.fixture
def server(session):
    server = MediaServer(
        name="Nick Server", server_type="jellyfin", url="http://nick", api_key="k"
    )
    session.add(server)
    session.commit()
    yield server
    # The session fixture does not delete identities. Delete the users first.
    User.query.delete()
    Identity.query.delete()
    session.commit()


def _user(server, username, email):
    user = User(
        token=f"t-{username}",
        username=username,
        email=email,
        code=f"C-{username}",
        server_id=server.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _load(model, pk):
    row = db.session.get(model, pk)
    assert row is not None
    return row


def test_single_account_user_card_has_edit_button(admin_client, app, server):
    with app.app_context():
        user = _user(server, "solo", "solo@example.com")
        user_id = user.id
        assert user.identity_id is None

    body = admin_client.get("/users/table").get_data(as_text=True)
    assert f"/user/{user_id}/nickname" in body


def test_single_account_user_can_be_named(admin_client, app, server):
    with app.app_context():
        user_id = _user(server, "solo", "solo@example.com").id

    assert admin_client.get(f"/user/{user_id}/nickname").status_code == 200
    resp = admin_client.post(f"/user/{user_id}/nickname", data={"nickname": "Sam"})
    assert resp.status_code == 200

    with app.app_context():
        identity = _load(User, user_id).identity
        assert identity is not None
        assert identity.nickname == "Sam"
        assert identity.primary_email == "solo@example.com"

    body = admin_client.get("/users/table").get_data(as_text=True)
    assert "Sam" in body


def test_save_does_not_swap_the_table_and_triggers_a_refresh(admin_client, app, server):
    """The save response is empty. If the form swapped it into #user_table,
    the table disappeared when its refresh took longer than the swap delay."""
    with app.app_context():
        user_id = _user(server, "solo", "solo@example.com").id

    form = admin_client.get(f"/user/{user_id}/nickname").get_data(as_text=True)
    assert 'hx-swap="none"' in form
    assert 'hx-target="#user_table"' not in form

    resp = admin_client.post(f"/user/{user_id}/nickname", data={"nickname": "Sam"})
    triggers = {t.strip() for t in resp.headers["HX-Trigger"].split(",")}
    assert {"closeModal", "refreshUserTable"} <= triggers


def test_opening_or_saving_empty_creates_no_identity(admin_client, app, server):
    with app.app_context():
        user_id = _user(server, "solo", "solo@example.com").id
        before = Identity.query.count()

    admin_client.get(f"/user/{user_id}/nickname")
    admin_client.post(f"/user/{user_id}/nickname", data={"nickname": "  "})

    with app.app_context():
        assert _load(User, user_id).identity_id is None
        assert Identity.query.count() == before


def test_renaming_reuses_the_existing_identity(admin_client, app, server):
    with app.app_context():
        user = _user(server, "solo", "solo@example.com")
        identity = Identity(primary_email=user.email, nickname="Old")
        db.session.add(identity)
        user.identity = identity
        db.session.commit()
        user_id, identity_id = user.id, identity.id

    admin_client.post(f"/user/{user_id}/nickname", data={"nickname": "Pat"})

    with app.app_context():
        user = _load(User, user_id)
        assert user.identity_id == identity_id
        assert _load(Identity, identity_id).nickname == "Pat"


def test_auto_link_keeps_a_named_identity(app, server):
    """A second account with the same email joins the named person, whichever
    account the database returns first."""
    with app.app_context():
        unnamed = _user(server, "second", "pat@example.com")
        named_account = _user(server, "first", "pat@example.com")
        named = Identity(primary_email="pat@example.com", nickname="Pat")
        db.session.add(named)
        named_account.identity = named
        db.session.commit()
        named_id = named.id

        _auto_link_identities()

        assert _load(User, unnamed.id).identity_id == named_id
        assert _load(Identity, named_id).nickname == "Pat"
