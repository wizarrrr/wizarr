"""The connection form has to submit the fields it requires.

Issue #1343: creating an Overseerr/Jellyseerr connection silently did nothing.
Clicking Create Connection returned HTTP 200 and no row appeared.
"""

from pathlib import Path

MODAL = (
    Path(__file__).resolve().parents[1] / "app/templates/modals/connection-form.html"
)


def test_required_fields_are_not_rendered_disabled():
    """Connection Name and Media Server were disabled for the overseerr type.

    Disabled inputs are not submitted, and both fields carry DataRequired, so
    validate_on_submit() failed on fields the user had no way to fill. The route
    then re-rendered the form without surfacing an error, which is why this
    looked like nothing happening rather than a validation failure.
    """
    modal = MODAL.read_text()

    assert "disabled=(form.connection_type.data == 'overseerr')" not in modal


def test_every_form_field_that_is_required_is_editable():
    """Guards the general shape rather than the one type that regressed."""
    for line in MODAL.read_text().splitlines():
        for field in ("form.name(", "form.media_server_id("):
            if field in line:
                assert "disabled" not in line, f"{field} rendered disabled"
