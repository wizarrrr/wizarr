"""
Performance regression tests for the admin pages (Users, dashboard, invitations).

- /users/table: the number of SQL statements does not grow with the number
  of users, and the table is paginated by identity group.
- /hx/users/sync: the refreshUserTable trigger is sent only when a sync ran.
- /server-health-card: the health data comes from the service in-process.
- /accepted-invites-card: the count and the page come from SQL.
- /expired-users/table: the history loads in chunks with "show more".
- /invite/table: the invitations are paginated and the query count is fixed.
"""

import datetime
import re
from contextlib import contextmanager

from flask import template_rendered
from sqlalchemy import event

from app.extensions import db
from app.models import (
    ExpiredUser,
    Identity,
    Invitation,
    Library,
    MediaServer,
    User,
    invitation_users,
)

ROUTES = "app.blueprints.admin.routes"
SERVICE = "app.services.media.service"


@contextmanager
def count_statements(app):
    """Collect the SQL statements that run in the block."""
    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, params, context, many):
        statements.append(statement)

    with app.app_context():
        engine = db.engine
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _data_statements(statements: list[str]) -> list[str]:
    """Drop the settings lookups. Other code caches them with a time limit,
    so they come in some requests and not in others. They do not depend on
    the number of rows."""
    return [s for s in statements if "FROM settings" not in s]


@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def _server(name="Perf Server", server_type="jellyfin"):
    server = MediaServer(
        name=name, server_type=server_type, url=f"http://{name}", api_key="k"
    )
    db.session.add(server)
    db.session.commit()
    return server


def _add_users(server, start, count, *, linked=False):
    """Add users with an invitation each. Linked users get an Identity with
    a second account, so that the card groups two rows."""
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    for i in range(start, start + count):
        code = f"CODE{i:04d}"
        db.session.add(Invitation(code=code, used=True, unlimited=False))
        identity = None
        if linked:
            identity = Identity(primary_username=f"user_{i:04d}", nickname=f"N{i}")
            db.session.add(identity)
            db.session.flush()
        db.session.add(
            User(
                token=f"t{i}",
                username=f"user_{i:04d}",
                email=f"user{i}@example.com",
                code=code,
                expires=now + datetime.timedelta(days=i + 1),
                server_id=server.id,
                identity_id=identity.id if identity else None,
            )
        )
        if linked:
            db.session.add(
                User(
                    token=f"t{i}b",
                    username=f"user_{i:04d}",
                    email=f"user{i}@example.com",
                    code=code,
                    server_id=server.id,
                    identity_id=identity.id,
                )
            )
    db.session.commit()


def _card_count(body: str) -> int:
    return body.count('class="sr-only link-check"')


# ─── /users/table ──────────────────────────────────────────────────────────


def test_users_table_query_count_does_not_grow_with_users(app, admin_client):
    with app.app_context():
        server = _server()
        server_id = server.id
        _add_users(server, 0, 3)
        _add_users(server, 3, 2, linked=True)

    with count_statements(app) as small:
        assert admin_client.get("/users/table").status_code == 200

    with app.app_context():
        server = db.session.get(MediaServer, server_id)
        _add_users(server, 5, 15)
        _add_users(server, 20, 10, linked=True)

    with count_statements(app) as large:
        response = admin_client.get("/users/table")
    assert response.status_code == 200
    assert _card_count(response.data.decode()) == 30

    # No per-user invitation or identity lookups, and no UPDATE from the
    # display-only changes on the card objects.
    small, large = _data_statements(small), _data_statements(large)
    assert len(large) == len(small), (small, large)
    assert not any(s.lstrip().upper().startswith("UPDATE") for s in large)


def test_users_table_paginates_identity_groups(app, admin_client, monkeypatch):
    monkeypatch.setattr(f"{ROUTES}.USERS_PAGE_SIZE", 4)
    with app.app_context():
        server = _server()
        server_id = server.id
        _add_users(server, 0, 6)
        # Two linked rows for one person: one card, not two.
        _add_users(server, 6, 1, linked=True)

    page1 = admin_client.get("/users/table").data.decode()
    page2 = admin_client.get("/users/table", query_string={"page": 2}).data.decode()

    assert _card_count(page1) == 4
    assert _card_count(page2) == 3
    assert "user_0000" in page1 and "user_0003" in page1
    assert "user_0004" in page2 and "N6" in page2
    assert "user_0004" not in page1
    assert 'id="users_page" name="page" value="2"' in page2
    assert "1 / 2" in page1 and "2 / 2" in page2

    # A page after the last page shows the last page.
    clamped = admin_client.get("/users/table", query_string={"page": 99}).data.decode()
    assert 'id="users_page" name="page" value="2"' in clamped

    # The filters still apply when a page is given.
    searched = admin_client.get(
        "/users/table", query_string={"q": "user_0005", "page": 1}
    ).data.decode()
    assert _card_count(searched) == 1
    other = admin_client.get(
        "/users/table", query_string={"server": server_id + 1000}
    ).data.decode()
    assert _card_count(other) == 0


def test_users_table_expiry_sort_is_global_across_pages(app, admin_client, monkeypatch):
    monkeypatch.setattr(f"{ROUTES}.USERS_PAGE_SIZE", 2)
    with app.app_context():
        server = _server()
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        identity = Identity(primary_username="linked")
        db.session.add(identity)
        db.session.flush()
        rows = [
            ("d3", 3, None),
            ("never", None, None),
            ("d5", 5, None),
            ("linked", 60, identity.id),
            ("linked", 1, identity.id),
            ("d2", 2, None),
        ]
        for i, (name, days, identity_id) in enumerate(rows):
            db.session.add(
                User(
                    token=f"s{i}",
                    username=name,
                    email=f"{name}{i}@example.com",
                    code="None",
                    expires=now + datetime.timedelta(days=days) if days else None,
                    server_id=server.id,
                    identity_id=identity_id,
                )
            )
        db.session.commit()

    def names(page, order):
        body = admin_client.get(
            "/users/table", query_string={"order": order, "page": page}
        ).data.decode()
        return re.findall(r'<h3 class="font-semibold[^"]*">([^<]+)</h3>', body)

    asc = names(1, "expires_asc") + names(2, "expires_asc") + names(3, "expires_asc")
    assert asc == ["linked", "d2", "d3", "d5", "never"]

    desc = (
        names(1, "expires_desc") + names(2, "expires_desc") + names(3, "expires_desc")
    )
    assert desc == ["never", "d5", "d3", "d2", "linked"]


def test_users_table_partial_adds_no_listeners(app, admin_client):
    body = admin_client.get("/users/table").data.decode()
    # A table render must not add document listeners (they add up on each
    # refresh). The listeners are in admin/users.html, behind a guard flag.
    assert "<script" not in body


def test_users_page_refreshes_table_from_body_and_lists_expired_once(app, admin_client):
    with app.app_context():
        server = _server()
        db.session.add(
            ExpiredUser(
                original_user_id=1,
                username="gone_user",
                server_id=server.id,
                expired_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
            )
        )
        db.session.commit()

    body = admin_client.get("/users", headers={"HX-Request": "true"}).data.decode()
    assert 'hx-trigger="load, refreshUserTable from:body"' in body
    assert "#users_page" in body
    assert "window.wizarrUsersPageListeners" in body
    # The expired list loads one time, from /expired-users/table.
    assert "gone_user" not in body
    assert "Recently Expired Users" not in body
    assert 'hx-get="/expired-users/table"' in body
    # The manual sync button forces a sync.
    assert 'hx-get="/hx/users/sync?force=1"' in body


# ─── /hx/users/sync ────────────────────────────────────────────────────────


def test_sync_route_triggers_refresh_only_when_sync_ran(app, admin_client, monkeypatch):
    calls = []
    result = {"value": False}

    def fake_sync_users(server=None, *, force=False, max_age=300.0):
        calls.append((server, force))
        return result["value"]

    monkeypatch.setattr(f"{SERVICE}.sync_users", fake_sync_users, raising=False)

    response = admin_client.get("/hx/users/sync", query_string={"server": ""})
    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers
    assert calls[-1] == (None, False)

    result["value"] = True
    response = admin_client.get("/hx/users/sync")
    assert response.headers.get("HX-Trigger") == "refreshUserTable"

    response = admin_client.get("/hx/users/sync", query_string={"force": "1"})
    assert calls[-1] == (None, True)
    assert response.headers.get("HX-Trigger") == "refreshUserTable"

    with app.app_context():
        server_id = _server().id
    admin_client.get("/hx/users/sync", query_string={"server": server_id})
    assert calls[-1][0].id == server_id
    assert calls[-1][1] is False


# ─── /server-health-card ───────────────────────────────────────────────────


def test_server_health_card_uses_in_process_health(app, admin_client, monkeypatch):
    def no_http(*args, **kwargs):
        raise AssertionError("the health card must not make an HTTP request")

    monkeypatch.setattr("requests.get", no_http)

    health = {
        2: {
            "server_name": "Beta",
            "server_type": "plex",
            "server_id": 2,
            "user_stats": {"total_users": 7, "active_sessions": 0},
            "server_stats": {"version": "1.2.3", "transcoding_sessions": 0},
            "library_stats": {},
            "content_stats": {},
        },
        1: {
            "server_name": "Alpha",
            "server_type": "jellyfin",
            "server_id": 1,
            "error": "Failed to get health: offline",
            "user_stats": {"total_users": 0, "active_sessions": 0},
            "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
            "library_stats": {},
            "content_stats": {},
        },
        3: {
            "server_name": "Gamma",
            "server_type": "emby",
            "server_id": 3,
            "user_stats": {"total_users": 2, "active_sessions": 4},
            "server_stats": {"version": "4.8", "transcoding_sessions": 1},
            "library_stats": {},
            "content_stats": {},
        },
    }
    monkeypatch.setattr(
        f"{SERVICE}.get_all_server_health",
        lambda *, use_cache=True: health,
        raising=False,
    )
    sessions = [
        {"server_id": 2, "transcoding_info": {"is_transcoding": True}},
        {"server_id": 2, "transcoding_info": {}},
        {"server_id": None},
    ]
    monkeypatch.setattr(f"{ROUTES}.get_now_playing_all_servers", lambda: sessions)

    with captured_templates(app) as templates:
        response = admin_client.get("/server-health-card")
    assert response.status_code == 200
    _, context = templates[-1]
    assert context["success"] is True
    servers = context["servers"]

    # Online servers first, then by name.
    assert [s["name"] for s in servers] == ["Beta", "Gamma", "Alpha"]
    beta, gamma, alpha = servers
    assert beta["online"] and beta["active_sessions"] == 2
    assert beta["transcoding"] == 1 and beta["total_users"] == 7
    assert beta["version"] == "1.2.3"
    # No now-playing sessions: use the counts from the health stats.
    assert gamma["active_sessions"] == 4 and gamma["transcoding"] == 1
    assert not alpha["online"] and "offline" in alpha["error"]


def test_server_health_card_shows_error_when_service_fails(
    app, admin_client, monkeypatch
):
    def broken(*, use_cache=True):
        raise RuntimeError("boom")

    monkeypatch.setattr(f"{SERVICE}.get_all_server_health", broken, raising=False)
    response = admin_client.get("/server-health-card")
    assert response.status_code == 200
    assert "boom" in response.data.decode()


# ─── /accepted-invites-card ────────────────────────────────────────────────


def test_accepted_invites_card_counts_and_pages_in_sql(app, admin_client):
    with app.app_context():
        server = _server()  # one server → 3 rows per page
        base = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
        for i in range(7):
            user = User(
                token=f"a{i}",
                username=f"joined_{i}",
                email=f"j{i}@example.com",
                code=f"ACC{i}",
                server_id=server.id,
            )
            invite = Invitation(code=f"ACC{i}", used=True, unlimited=False)
            db.session.add_all([user, invite])
            db.session.flush()
            db.session.execute(
                invitation_users.insert().values(
                    invite_id=invite.id,
                    user_id=user.id,
                    used_at=base + datetime.timedelta(hours=i),
                )
            )
        db.session.commit()

    with captured_templates(app) as templates, count_statements(app) as statements:
        response = admin_client.get("/accepted-invites-card", query_string={"page": 2})
    assert response.status_code == 200
    _, context = templates[-1]
    assert context["total"] == 7
    assert context["total_pages"] == 3
    assert (context["start_index"], context["end_index"]) == (4, 6)
    assert [u.username for u in context["recent_users"]] == [
        "joined_3",
        "joined_2",
        "joined_1",
    ]
    joined = " ".join(statements).lower()
    assert "count(" in joined
    assert "limit" in joined

    with captured_templates(app) as templates:
        admin_client.get("/accepted-invites-card", query_string={"page": 99})
    _, context = templates[-1]
    assert context["page"] == 3
    assert [u.username for u in context["recent_users"]] == ["joined_0"]


# ─── /expired-users/table ──────────────────────────────────────────────────


def test_expired_users_table_loads_in_chunks(app, admin_client, monkeypatch):
    monkeypatch.setattr(f"{ROUTES}.EXPIRED_USERS_PAGE_SIZE", 4)
    with app.app_context():
        base = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
        for i in range(6):
            db.session.add(
                ExpiredUser(
                    original_user_id=100 + i,
                    username=f"expired_{i}",
                    expired_at=base,
                    deleted_at=base + datetime.timedelta(hours=i),
                )
            )
        db.session.commit()

    first = admin_client.get("/expired-users/table").data.decode()
    assert 'id="expired_users_table"' in first
    assert len(re.findall(r">expired_\d+<", first)) == 4
    assert "expired_5" in first and "expired_1" not in first
    assert 'hx-get="/expired-users/table?offset=4"' in first
    assert "6 expired user" in first

    more = admin_client.get("/expired-users/table", query_string={"offset": 4})
    body = more.data.decode()
    assert 'id="expired_users_table"' not in body
    assert "expired_1" in body and "expired_0" in body
    assert "expired_5" not in body
    assert "offset=" not in body  # no more rows → no button


# ─── /invite/table ─────────────────────────────────────────────────────────


def _add_invites(server, start, count):
    library = Library.query.filter_by(server_id=server.id).first()
    if library is None:
        library = Library(external_id="lib1", name="Movies", server_id=server.id)
        db.session.add(library)
        db.session.flush()
    base = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
    for i in range(start, start + count):
        invite = Invitation(
            code=f"INV{i:04d}",
            used=False,
            unlimited=False,
            created=base + datetime.timedelta(hours=i),
        )
        invite.servers.append(server)
        invite.libraries.append(library)
        db.session.add(invite)
    db.session.commit()


def test_invite_table_query_count_does_not_grow_with_invites(app, admin_client):
    with app.app_context():
        server = _server(server_type="plex")
        server_id = server.id
        _add_invites(server, 0, 2)

    with count_statements(app) as small:
        assert admin_client.post("/invite/table").status_code == 200

    with app.app_context():
        _add_invites(db.session.get(MediaServer, server_id), 2, 10)

    with count_statements(app) as large:
        response = admin_client.post("/invite/table")
    assert response.status_code == 200
    assert response.data.decode().count('class="sr-only invite-check"') == 12
    small, large = _data_statements(small), _data_statements(large)
    assert len(large) == len(small), (small, large)
    # The used flags come only for the invitations on the page.
    flag_queries = [s for s in large if "FROM invitation_server" in s]
    assert flag_queries
    assert all("invite_id IN" in s for s in flag_queries if "WHERE" in s)


def test_invite_table_paginates(app, admin_client, monkeypatch):
    monkeypatch.setattr(f"{ROUTES}.INVITES_PAGE_SIZE", 2)
    with app.app_context():
        server = _server(server_type="plex")
        server_id = server.id
        _add_invites(server, 0, 5)

    page1 = admin_client.post("/invite/table").data.decode()
    page3 = admin_client.post("/invite/table", data={"page": "3"}).data.decode()

    # Newest first
    assert "INV0004" in page1 and "INV0003" in page1 and "INV0002" not in page1
    assert "INV0000" in page3 and "INV0001" not in page3
    assert "1 / 3" in page1 and "3 / 3" in page3
    assert 'hx-include="#invite_server_filter"' in page1

    # The server filter still applies with a page number.
    filtered = admin_client.post(
        "/invite/table", data={"server": str(server_id + 1000), "page": "2"}
    ).data.decode()
    assert "INV000" not in filtered


def test_invite_delete_keeps_the_page_and_the_filter(app, admin_client, monkeypatch):
    monkeypatch.setattr(f"{ROUTES}.INVITES_PAGE_SIZE", 2)
    with app.app_context():
        server = _server(server_type="plex")
        server_id = server.id
        _add_invites(server, 0, 5)
        delete_id = Invitation.query.filter_by(code="INV0002").one().id

    # The table has the page field that the delete button includes.
    page2 = admin_client.post("/invite/table", data={"page": "2"}).data.decode()
    assert 'id="invite_page"' in page2

    modal = admin_client.get(f"/invite/{delete_id}/delete-modal").data.decode()
    assert 'hx-include="#invite_server_filter,#invite_page"' in modal

    # The delete button sends the values of the included fields.
    body = admin_client.post(
        f"/invite/table?delete_id={delete_id}",
        data={"server": str(server_id), "page": "2"},
    ).data.decode()

    assert "INV0002" not in body
    assert "INV0001" in body and "INV0000" in body
    assert "2 / 2" in body


# ─── Dashboard polling ─────────────────────────────────────────────────────


def test_dashboard_polls_only_in_visible_tabs(app, admin_client):
    body = admin_client.get("/home", headers={"HX-Request": "true"}).data.decode()
    visible = "[document.visibilityState === 'visible']"
    for interval in ("10s", "30s", "45s"):
        assert f"every {interval} {visible}" in body
    assert f"visibilitychange{visible} from:document" in body
    assert "let liveTimers" not in body
