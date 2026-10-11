"""
Regression tests: sorting the users table by expiry date.

Covers ascending/descending sort by `User.expires`, placement of
"never expires" (NULL) users, and grouped/linked identities sorting by
their earliest expiring account regardless of which underlying row the
raw query surfaces first.
"""

import datetime

import pytest

from app.extensions import db
from app.models import AdminAccount, Identity, MediaServer, User


@pytest.fixture
def admin_user(app):
    """Create an admin account for authenticated requests."""
    with app.app_context():
        created = False
        previous_hash = None
        admin = AdminAccount.query.filter_by(username="testadmin").first()
        if not admin:
            admin = AdminAccount(username="testadmin")
            admin.set_password("TestPass123")
            db.session.add(admin)
            db.session.commit()
            created = True
        else:
            previous_hash = admin.password_hash
            admin.set_password("TestPass123")
            db.session.commit()
        yield admin
        if created:
            db.session.delete(admin)
            db.session.commit()
        elif previous_hash is not None:
            admin = AdminAccount.query.filter_by(username="testadmin").first()
            if admin:
                admin.password_hash = previous_hash
                db.session.commit()


def _login(client):
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})


def _usernames_in_order(body: str, usernames: list[str]) -> list[str]:
    """Return `usernames` ordered by their first appearance in `body`."""
    positions = {name: body.find(name) for name in usernames}
    return sorted(
        (name for name in usernames if positions[name] != -1),
        key=lambda name: positions[name],
    )


def test_users_table_sorts_by_expires_ascending(client, app, session, admin_user):
    """expires_asc orders soonest-to-expire first, never-expires users last."""
    with app.app_context():
        server = MediaServer(
            name="Sort Server", server_type="jellyfin", url="http://sort", api_key="k1"
        )
        db.session.add(server)
        db.session.commit()

        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        soon = User(
            token="t-soon",
            username="user_soon",
            email="soon@example.com",
            code="SOON",
            expires=now + datetime.timedelta(days=1),
            server_id=server.id,
        )
        later = User(
            token="t-later",
            username="user_later",
            email="later@example.com",
            code="LATER",
            expires=now + datetime.timedelta(days=30),
            server_id=server.id,
        )
        never = User(
            token="t-never",
            username="user_never",
            email="never@example.com",
            code="NEVER",
            expires=None,
            server_id=server.id,
        )
        db.session.add_all([soon, later, never])
        db.session.commit()

    _login(client)
    response = client.get("/users/table", query_string={"order": "expires_asc"})
    assert response.status_code == 200
    body = response.data.decode("utf-8")

    order = _usernames_in_order(body, ["user_soon", "user_later", "user_never"])
    assert order == ["user_soon", "user_later", "user_never"]


def test_users_table_sorts_by_expires_descending(client, app, session, admin_user):
    """expires_desc orders latest-to-expire first, never-expires users first."""
    with app.app_context():
        server = MediaServer(
            name="Sort Server 2",
            server_type="jellyfin",
            url="http://sort2",
            api_key="k2",
        )
        db.session.add(server)
        db.session.commit()

        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        soon = User(
            token="t-soon2",
            username="user_soon2",
            email="soon2@example.com",
            code="SOON2",
            expires=now + datetime.timedelta(days=1),
            server_id=server.id,
        )
        later = User(
            token="t-later2",
            username="user_later2",
            email="later2@example.com",
            code="LATER2",
            expires=now + datetime.timedelta(days=30),
            server_id=server.id,
        )
        never = User(
            token="t-never2",
            username="user_never2",
            email="never2@example.com",
            code="NEVER2",
            expires=None,
            server_id=server.id,
        )
        db.session.add_all([soon, later, never])
        db.session.commit()

    _login(client)
    response = client.get("/users/table", query_string={"order": "expires_desc"})
    assert response.status_code == 200
    body = response.data.decode("utf-8")

    order = _usernames_in_order(body, ["user_soon2", "user_later2", "user_never2"])
    assert order == ["user_never2", "user_later2", "user_soon2"]


def test_users_table_sorts_linked_identity_by_earliest_expiry(
    client, app, session, admin_user
):
    """Linked accounts collapse into one card, sorted by their earliest expiry
    in both ascending and descending order (not by whichever raw row the
    query surfaces first)."""
    with app.app_context():
        srv_a = MediaServer(
            name="Linked A", server_type="plex", url="http://linkeda", api_key="ka"
        )
        srv_b = MediaServer(
            name="Linked B", server_type="jellyfin", url="http://linkedb", api_key="kb"
        )
        db.session.add_all([srv_a, srv_b])
        db.session.commit()

        identity = Identity(primary_username="linked_user")
        db.session.add(identity)
        db.session.commit()

        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        # Linked identity's earliest account expires soon; its other account
        # expires far in the future.
        linked_early = User(
            token="t-link-early",
            username="linked_user",
            email="linked@example.com",
            code="LINKEARLY",
            expires=now + datetime.timedelta(days=2),
            server_id=srv_a.id,
            identity_id=identity.id,
        )
        linked_late = User(
            token="t-link-late",
            username="linked_user",
            email="linked@example.com",
            code="LINKLATE",
            expires=now + datetime.timedelta(days=60),
            server_id=srv_b.id,
            identity_id=identity.id,
        )
        # A standalone user in between the two expiry dates.
        middle = User(
            token="t-middle",
            username="user_middle",
            email="middle@example.com",
            code="MIDDLE",
            expires=now + datetime.timedelta(days=10),
            server_id=srv_a.id,
        )
        db.session.add_all([linked_early, linked_late, middle])
        db.session.commit()

    _login(client)

    asc_response = client.get("/users/table", query_string={"order": "expires_asc"})
    asc_body = asc_response.data.decode("utf-8")
    asc_order = _usernames_in_order(asc_body, ["linked_user", "user_middle"])
    assert asc_order == ["linked_user", "user_middle"]

    desc_response = client.get("/users/table", query_string={"order": "expires_desc"})
    desc_body = desc_response.data.decode("utf-8")
    desc_order = _usernames_in_order(desc_body, ["linked_user", "user_middle"])
    # Even descending, the linked card stays positioned by its earliest
    # (soonest) expiry, so it appears AFTER user_middle (day 10).
    assert desc_order == ["user_middle", "linked_user"]
