"""Linked accounts show the account that has a real e-mail address (#1277).

The link route used users[0] from a query without ORDER BY, and the user card
used the account with the smallest username. Thus a Jellyfin account with the
placeholder e-mail "empty" could become the primary account, and the result of
a merge looked random.
"""

import pytest

from app.extensions import db
from app.models import Identity, MediaServer, User


@pytest.fixture
def accounts(session):
    jellyfin = MediaServer(
        name="Jellyfin", server_type="jellyfin", url="http://jf", api_key="k"
    )
    plex = MediaServer(name="Plex", server_type="plex", url="http://plex", api_key="k")
    session.add_all([jellyfin, plex])
    session.commit()
    # The Jellyfin account has the lower id and the username that sorts first.
    jf_user = User(
        username="John", email="empty", token="t1", code="C1", server_id=jellyfin.id
    )
    session.add(jf_user)
    session.commit()
    plex_user = User(
        username="john",
        email="john@example.com",
        token="t2",
        code="C2",
        server_id=plex.id,
    )
    session.add(plex_user)
    session.commit()
    yield jf_user, plex_user
    session.query(User).delete()
    Identity.query.filter(~Identity.accounts.any()).delete(synchronize_session=False)
    session.commit()


def test_link_uses_the_account_with_a_real_email(admin_client, accounts):
    jf_user, plex_user = accounts

    response = admin_client.post(
        "/users/link", data={"uids": [str(jf_user.id), str(plex_user.id)]}
    )

    assert response.status_code == 200
    linked = db.session.get(User, jf_user.id)
    assert linked is not None
    identity = linked.identity
    assert identity.primary_email == "john@example.com"
    assert identity.primary_username == "john"


def test_card_shows_the_real_email_and_keeps_jellyfin_reset(
    admin_client, session, accounts
):
    jf_user, plex_user = accounts
    identity = Identity()
    session.add(identity)
    session.flush()
    jf_user.identity_id = plex_user.identity_id = identity.id
    session.commit()

    html = admin_client.get("/users/table").get_data(as_text=True)

    assert 'truncate">john@example.com</p>' in html
    assert 'truncate">empty</p>' not in html
    # The Jellyfin account is not the primary account, but it can still reset.
    assert f"/users/{jf_user.id}/reset-password-modal" in html
