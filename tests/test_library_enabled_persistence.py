"""Library.enabled is the admin's saved default for new invites.

It is written by the server edit form, rendered as `checked` by
partials/library_checkboxes.html, and used by _invite_user as the fallback library
set for invites that carry none of their own. Library scans must therefore not
reset it, and the legacy settings scan must not delete rows it does not own.
"""

from unittest.mock import Mock, patch

import pytest

from app.models import Library, MediaServer
from app.services.media.service import upsert_scanned_libraries


def _server(session, name="Plex"):
    server = MediaServer(
        name=name, server_type="plex", url="http://plex.local", api_key="token"
    )
    session.add(server)
    session.commit()
    return server


def _libs(session, server, spec):
    """spec: {external_id: (name, enabled)}"""
    for ext, (name, enabled) in spec.items():
        session.add(
            Library(external_id=ext, name=name, server_id=server.id, enabled=enabled)
        )
    session.commit()


def _enabled_map(server_id):
    return {
        lib.external_id: lib.enabled
        for lib in Library.query.filter_by(server_id=server_id).all()
    }


SCAN_RESULT = {"1": "Movies", "2": "TV Shows", "3": "Home Video"}


def test_invite_scan_rendered_checkboxes_match_enabled(admin_client, session):
    """The rendered form must offer every library but pre-check only the enabled ones."""
    server = _server(session)
    _libs(
        session,
        server,
        {"1": ("Movies", True), "2": ("TV Shows", False), "3": ("Home Video", False)},
    )

    with patch(
        "app.blueprints.admin.routes.scan_libraries_for_server",
        return_value=(SCAN_RESULT, True),
    ):
        resp = admin_client.post(
            "/invite/scan-libraries", data={"server_ids": str(server.id)}
        )

    html = resp.get_data(as_text=True)
    assert html.count('name="libraries"') == 3
    assert html.count("checked") == 1


@pytest.mark.parametrize(
    ("scan", "authoritative", "expected"),
    [
        # A short scan that the client marks unreliable drops nothing.
        ({"2": "TV Shows"}, False, {"1": True, "2": True}),
        # A reliable scan removes a library that is gone.
        ({"2": "TV Shows"}, True, {"2": True}),
    ],
)
def test_invite_scan_passes_the_authoritative_flag(
    admin_client, session, scan, authoritative, expected
):
    server = _server(session)
    _libs(session, server, {"1": ("Movies", True), "2": ("TV Shows", True)})

    with patch(
        "app.blueprints.admin.routes.scan_libraries_for_server",
        return_value=(scan, authoritative),
    ):
        resp = admin_client.post(
            "/invite/scan-libraries", data={"server_ids": str(server.id)}
        )

    assert resp.status_code == 200
    assert _enabled_map(server.id) == expected


def test_server_edit_scan_preserves_disabled_libraries(admin_client, session):
    """The scan that the server edit form runs keeps a disabled library."""
    server = _server(session)
    _libs(session, server, {"1": ("Movies", True), "3": ("Home Video", False)})

    with patch(
        "app.blueprints.media_servers.routes.scan_libraries_for_server",
        return_value=(SCAN_RESULT, True),
    ):
        resp = admin_client.post(f"/settings/servers/{server.id}/scan-libraries")
    assert resp.status_code == 200

    enabled = _enabled_map(server.id)
    assert enabled["1"] is True
    assert enabled["3"] is False


@pytest.mark.parametrize(
    ("existing", "scan", "authoritative", "expected"),
    [
        pytest.param(
            {"1": ("Movies", True), "2": ("TV Shows", True), "3": ("Home", False)},
            SCAN_RESULT,
            True,
            {"1": True, "2": True, "3": False},
            id="keeps-disabled-library",
        ),
        pytest.param(
            {"1": ("Movies", True)},
            SCAN_RESULT,
            True,
            {"1": True, "2": True, "3": True},
            id="new-library-is-enabled",
        ),
        # Regression: a 12-library server came back as a 7-library scan and
        # dropped Movies and TV Shows from the invite default. The client tells
        # if a scan is reliable (libraries_scan_authoritative). The count does
        # not: a same-size scan can have a different library in it.
        pytest.param(
            {
                "1": ("Movies", True),
                "2": ("TV Shows", True),
                "3": ("Home", False),
                "4": ("Music", False),
            },
            {"3": "Home", "4": "Music"},
            False,
            {"1": True, "2": True, "3": False, "4": False},
            id="unreliable-short-scan",
        ),
        pytest.param(
            {"1": ("Movies", True), "2": ("TV Shows", True)},
            {"2": "TV Shows", "3": "Documentaries"},
            False,
            {"1": True, "2": True, "3": True},
            id="unreliable-same-size-scan",
        ),
        # A real removal must not stay blocked because the count gets smaller.
        # Nothing refers to library 1, so the scan deletes it.
        pytest.param(
            {"1": ("Movies", True), "2": ("TV Shows", True)},
            {"2": "TV Shows"},
            True,
            {"2": True},
            id="reliable-scan-removes-library",
        ),
        # Plex can give no sections for a short time. That must not wipe the table.
        pytest.param(
            {"1": ("Movies", True), "3": ("Home", False)},
            {},
            True,
            {"1": True, "3": False},
            id="empty-scan",
        ),
    ],
)
def test_upsert_scanned_libraries(session, existing, scan, authoritative, expected):
    server = _server(session)
    _libs(session, server, existing)

    upsert_scanned_libraries(server, scan, authoritative=authoritative)
    session.commit()

    assert _enabled_map(server.id) == expected


def test_malformed_scan_result_does_not_abort_other_servers(admin_client, session):
    """A malformed scan result (e.g. ``None``) for one server must not raise out
    of the reconciliation loop and discard already-processed servers in the same
    multi-server scan request.
    """
    bad_server = _server(session, name="Bad")
    good_server = _server(session, name="Good")

    def fake_scan(server):
        if server.id == bad_server.id:
            return None, True
        return SCAN_RESULT, True

    with patch(
        "app.blueprints.admin.routes.scan_libraries_for_server",
        side_effect=fake_scan,
    ):
        resp = admin_client.post(
            "/invite/scan-libraries",
            data={"server_ids": [str(bad_server.id), str(good_server.id)]},
        )
    assert resp.status_code == 200

    assert _enabled_map(good_server.id) == {"1": True, "2": True, "3": True}


def test_legacy_settings_scan_does_not_delete_other_servers_libraries(
    admin_client, session
):
    """The legacy route owns only unbound rows; it must not touch real servers'."""
    server = _server(session, name="Existing")
    _libs(session, server, {"1": ("Movies", True), "3": ("Home Video", False)})
    session.add(Library(external_id="stale", name="Stale", server_id=None))
    session.commit()

    bound_ids_before = {
        lib.id for lib in Library.query.filter_by(server_id=server.id).all()
    }

    with patch(
        "app.blueprints.settings.routes.scan_media", return_value={"9": "Fresh"}
    ):
        resp = admin_client.post(
            "/settings/scan-libraries",
            data={
                "server_type": "plex",
                "server_url": "http://plex.local",
                "api_key": "token",
            },
        )
    assert resp.status_code == 200

    bound_after = Library.query.filter_by(server_id=server.id).all()
    assert {lib.id for lib in bound_after} == bound_ids_before
    assert _enabled_map(server.id) == {"1": True, "3": False}

    # the unbound staging rows are still replaced, which is this route's job
    unbound = {lib.external_id for lib in Library.query.filter_by(server_id=None).all()}
    assert unbound == {"9"}


# --- startup scan -----------------------------------------------------------
# scan_all_server_libraries runs from create_app on every boot. It used to carry
# its own copy of the upsert, which re-enabled every existing library it saw, so
# a disabled library came back on the next restart. It now delegates to
# upsert_scanned_libraries like the admin-triggered scans do. The tests above
# check the upsert rules; these tests check the startup path.


def _startup_scan(scan_result):
    """Drive the startup scan with a stubbed media client.

    Patches the client factory rather than scan_libraries_for_server so the test
    exercises whatever path the scanner takes internally, and fails on behaviour
    rather than on which helper happens to be called.
    """
    from app.services.library_scanner import scan_all_server_libraries

    client = Mock()
    client.libraries.return_value = scan_result
    client.libraries_scan_authoritative.return_value = True

    with patch(
        "app.services.media.service.get_client_for_media_server",
        return_value=client,
    ):
        return scan_all_server_libraries(show_logs=False)


def test_startup_scan_preserves_disabled_libraries(session):
    """A restart must not re-share a library the admin excluded."""
    server = _server(session)
    _libs(
        session,
        server,
        {"1": ("Movies", True), "2": ("TV Shows", True), "3": ("Home Video", False)},
    )

    total, errors = _startup_scan(SCAN_RESULT)

    assert errors == []
    assert total == 3
    assert _enabled_map(server.id) == {"1": True, "2": True, "3": False}


def test_startup_scan_renames_without_re_enabling(session):
    server = _server(session)
    _libs(session, server, {"3": ("Old Name", False)})

    _startup_scan({"3": "New Name"})

    lib = Library.query.filter_by(external_id="3").one()
    assert lib.name == "New Name"
    assert lib.enabled is False
