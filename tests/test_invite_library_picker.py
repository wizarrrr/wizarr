from html.parser import HTMLParser
from unittest.mock import patch

from app.models import Library, MediaServer


class _LabelNestingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.label_depth = 0
        self.lib_menu_ids_inside_labels: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "label":
            self.label_depth += 1

        element_id = attrs_dict.get("id", "")
        if self.label_depth and element_id.startswith("libMenu"):
            self.lib_menu_ids_inside_labels.append(element_id)

    def handle_endtag(self, tag):
        if tag == "label" and self.label_depth:
            self.label_depth -= 1


def _plex_server(session, name):
    server = MediaServer(
        name=name,
        server_type="plex",
        url="http://plex.local",
        api_key="plex-token",
        verified=True,
    )
    session.add(server)
    session.commit()
    return server


def _invite_form(client):
    response = client.get("/invite", headers={"HX-Request": "true"})
    assert response.status_code == 200
    return response.data.decode("utf-8")


def test_invite_form_keeps_library_dropdown_outside_server_label(admin_client, session):
    server = _plex_server(session, "Plex With Many Libraries")

    html = _invite_form(admin_client)

    parser = _LabelNestingParser()
    parser.feed(html)
    assert parser.lib_menu_ids_inside_labels == []
    assert f'aria-controls="libMenu{server.id}"' in html
    assert 'data-dropdown-toggle="libMenu' not in html


def test_invite_form_scans_libraries_only_until_dropdown_is_loaded(
    admin_client, session
):
    server = _plex_server(session, "Plex Server")

    html = _invite_form(admin_client)

    assert (
        f"hx-trigger=\"click[!isLibraryDropdownLoaded('libMenu{server.id}')]\"" in html
    )


def test_invite_scan_libraries_renders_existing_choices_without_duplicate_ids(
    admin_client, session
):
    server = _plex_server(session, "Large Plex")
    scanned_libraries = {str(i): f"Library {i:02d}" for i in range(1, 21)}

    with patch(
        "app.blueprints.admin.routes.scan_libraries_for_server",
        return_value=(scanned_libraries, True),
    ):
        response = admin_client.post(
            "/invite/scan-libraries",
            data={"server_ids": str(server.id)},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert html.count('name="libraries"') == 20

    saved_libraries = Library.query.filter_by(server_id=server.id).all()
    assert len(saved_libraries) == 20
    for library in saved_libraries:
        assert f'id="lib{server.id}-{library.id}"' in html
        assert f'value="{library.id}"' in html


def test_invite_modal_swaps_return_content_without_dialog(admin_client, session):
    server = MediaServer(
        name="Plex Server",
        server_type="plex",
        url="http://plex.local",
        api_key="plex-token",
        verified=True,
    )
    session.add(server)
    session.commit()

    opened = admin_client.get(
        "/invite", headers={"HX-Request": "true", "HX-Target": "invite-modal"}
    ).data.decode("utf-8")
    assert opened.count("<dialog") == 1
    assert opened.count('id="inviteModalContent"') == 1

    # "Create Another" and the form submit swap into #inviteModalContent.
    # A second dialog in that swap would nest the modal inside itself.
    swapped = admin_client.get(
        "/invite", headers={"HX-Request": "true", "HX-Target": "inviteModalContent"}
    ).data.decode("utf-8")
    assert "<dialog" not in swapped
    assert 'id="inviteModalContent"' not in swapped
    assert f'id="srv{server.id}"' in swapped
