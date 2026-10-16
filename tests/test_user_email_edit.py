"""
An admin can add or change the e-mail of an existing user (#1189).

Imported Jellyfin users have no address. Wizarr keeps the address only in its
own database. Plex and the other servers keep their own address, so Wizarr
does not change it for their accounts.
"""

import pytest

from app.extensions import db
from app.models import Identity, MediaServer, User
from app.services.user_email import (
    InvalidEmailError,
    current_email,
    set_user_email,
)


@pytest.fixture
def servers(app, session):
    with app.app_context():
        jellyfin = MediaServer(
            name="JF", server_type="jellyfin", url="http://jf", api_key="k"
        )
        plex = MediaServer(
            name="Plex", server_type="plex", url="http://px", api_key="k"
        )
        db.session.add_all([jellyfin, plex])
        db.session.commit()
        yield {"jellyfin": jellyfin.id, "plex": plex.id}
        User.query.delete()
        Identity.query.delete()
        db.session.commit()


def _user(server_id, username, email, identity=None):
    user = User(
        token=f"t-{username}",
        username=username,
        email=email,
        code="empty",
        server_id=server_id,
        identity=identity,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _load(user_id):
    user = db.session.get(User, user_id)
    assert user is not None
    return user


def _primary_email(identity_id):
    identity = db.session.get(Identity, identity_id)
    assert identity is not None
    return identity.primary_email


def test_set_email_on_imported_jellyfin_user(app, servers):
    with app.app_context():
        user = _user(servers["jellyfin"], "jf_only", "empty")
        assert current_email(user) == ""

        set_user_email(user, "  new@example.com ")
        db.session.commit()

        assert _load(user.id).email == "new@example.com"


def test_empty_value_removes_the_email(app, servers):
    with app.app_context():
        user = _user(servers["jellyfin"], "jf_clear", "old@example.com")

        set_user_email(user, "")
        db.session.commit()

        assert _load(user.id).email is None


def test_invalid_email_is_rejected(app, servers):
    with app.app_context():
        user = _user(servers["jellyfin"], "jf_bad", "old@example.com")

        with pytest.raises(InvalidEmailError):
            set_user_email(user, "not-an-address")

        assert user.email == "old@example.com"


def test_identity_keeps_one_address_and_plex_keeps_its_own(app, servers):
    with app.app_context():
        identity = Identity(primary_email="plex@example.com")
        plex = _user(servers["plex"], "pat_plex", "plex@example.com", identity)
        jellyfin = _user(servers["jellyfin"], "pat_jf", "empty", identity)

        # The admin can open the modal from the Plex card of the same person.
        set_user_email(plex, "pat@example.com")
        db.session.commit()

        assert _load(jellyfin.id).email == "pat@example.com"
        assert _load(plex.id).email == "plex@example.com"
        assert _primary_email(identity.id) == "pat@example.com"

        # Without a Wizarr address, the identity falls back to the Plex one.
        set_user_email(jellyfin, "")
        db.session.commit()

        assert _load(jellyfin.id).email is None
        assert _primary_email(identity.id) == "plex@example.com"


def test_modal_post_saves_email(admin_client, app, servers):
    with app.app_context():
        user_id = _user(servers["jellyfin"], "jf_post", "empty").id

    modal = admin_client.get(f"/user/{user_id}").get_data(as_text=True)
    assert 'name="email"' in modal

    resp = admin_client.post(f"/user/{user_id}", data={"email": "post@example.com"})
    assert resp.status_code == 200
    assert "closeModal" in resp.headers["HX-Trigger"]

    with app.app_context():
        assert _load(user_id).email == "post@example.com"


def test_modal_post_shows_error_for_invalid_email(admin_client, app, servers):
    with app.app_context():
        user_id = _user(servers["jellyfin"], "jf_post_bad", "old@example.com").id

    resp = admin_client.post(f"/user/{user_id}", data={"email": "user@localhost"})

    assert resp.headers["HX-Retarget"] == "#user-email-error"
    assert "HX-Trigger" not in resp.headers
    with app.app_context():
        assert _load(user_id).email == "old@example.com"


def test_modal_has_no_email_field_for_plex_only_user(admin_client, app, servers):
    with app.app_context():
        user_id = _user(servers["plex"], "plex_only", "plex@example.com").id

    modal = admin_client.get(f"/user/{user_id}").get_data(as_text=True)

    assert 'name="email"' not in modal
