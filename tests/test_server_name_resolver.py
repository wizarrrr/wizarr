"""Tests for the server name resolver of invitations."""

import pytest

from app.models import MediaServer, Settings
from app.services.server_name_resolver import (
    get_display_name_info,
    get_server_names_for_api,
    resolve_invitation_server_name,
)


@pytest.fixture
def servers(session):
    """A Plex server and a Jellyfin server, in this order."""
    plex = MediaServer(
        name="Plex Server",
        server_type="plex",
        url="http://localhost:32400",
        api_key="test_key1",
        verified=True,
    )
    jellyfin = MediaServer(
        name="Jellyfin Server",
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="test_key2",
        verified=True,
    )
    session.add_all([plex, jellyfin])
    session.commit()
    return [plex, jellyfin]


def _set_global_name(session, value):
    if value is not None:
        session.add(Settings(key="server_name", value=value))
        session.commit()


@pytest.mark.parametrize(
    ("server_count", "global_name", "expected"),
    [
        (1, None, "Plex Server"),
        # The default "Wizarr" value is not a custom name.
        (1, "Wizarr", "Plex Server"),
        (1, "My Custom Media Center", "My Custom Media Center"),
        (2, None, "Plex Server, Jellyfin Server"),
        (2, "My Home Media Hub", "My Home Media Hub"),
        (0, None, "Unknown Server"),
    ],
)
def test_resolve_invitation_server_name(
    session, servers, server_count, global_name, expected
):
    _set_global_name(session, global_name)
    assert resolve_invitation_server_name(servers[:server_count]) == expected


@pytest.mark.parametrize(
    ("server_count", "global_name", "expected"),
    [
        (
            2,
            None,
            {
                "display_name": "Plex Server, Jellyfin Server",
                "server_names": ["Plex Server", "Jellyfin Server"],
                "uses_global_setting": False,
                "global_setting_value": None,
            },
        ),
        (
            1,
            "Custom Name",
            {
                "display_name": "Custom Name",
                "server_names": ["Plex Server"],
                "uses_global_setting": True,
                "global_setting_value": "Custom Name",
            },
        ),
    ],
)
def test_get_display_name_info(session, servers, server_count, global_name, expected):
    _set_global_name(session, global_name)

    info = get_display_name_info(servers[:server_count])

    for key, value in expected.items():
        assert info[key] == value


def test_get_server_names_for_api(servers):
    assert get_server_names_for_api(servers) == ["Plex Server", "Jellyfin Server"]
    assert get_server_names_for_api([]) == []
