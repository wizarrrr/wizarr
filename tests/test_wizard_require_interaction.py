from __future__ import annotations

import contextlib
from pathlib import Path

from app.extensions import db
from app.models import WizardStep


def _enable_wizard_access(client):
    with client.session_transaction() as sess:
        sess["wizard_access"] = "test-code"


def test_db_step_requires_interaction_renders_next_disabled(app, client):
    # Arrange: create a DB-backed step that requires interaction
    with app.app_context():
        # Clean up any existing steps first to avoid unique constraint violations
        db.session.query(WizardStep).filter_by(server_type="plex").delete()
        db.session.commit()

        step = WizardStep(
            server_type="plex",
            category="post_invite",  # Explicitly set category
            position=0,
            title="Download",
            markdown="# Please download\n[Click me](https://example.com)",
            require_interaction=True,
        )
        db.session.add(step)
        db.session.commit()

    _enable_wizard_access(client)

    # Act - Initial page load (not HTMX) to get full UI chrome with buttons
    resp = client.get("/wizard/plex/0")

    # Assert
    assert resp.status_code == 200
    body = resp.data.decode()
    # After wizard overhaul, button IDs are prefixed with 'wizard-'
    assert 'id="wizard-next-btn"' in body
    # Next should be disabled when require_interaction is true
    assert 'data-disabled="1"' in body or 'aria-disabled="true"' in body


def test_file_based_front_matter_require_renders_next_disabled(app, client, tmp_path):
    # Arrange: create a temporary server folder with a markdown step that sets require: true
    wizard_steps_root = (
        Path("app/blueprints/wizard/routes.py").resolve().parent.parent.parent.parent
        / "wizard_steps"
    )
    test_server_dir = wizard_steps_root / "requiretest"
    test_server_dir.mkdir(parents=True, exist_ok=True)
    md_path = test_server_dir / "01_test.md"
    md_path.write_text(
        "---\n"
        "title: Require Test\n"
        "require: true\n"
        "---\n\n"
        "# Step\n\n"
        "[Do it](https://example.com)\n",
        encoding="utf-8",
    )

    _enable_wizard_access(client)

    try:
        # Act - Initial page load (not HTMX) to get full UI chrome with buttons
        resp = client.get("/wizard/requiretest/0")

        # Assert
        assert resp.status_code == 200
        body = resp.data.decode()
        # After wizard overhaul, button IDs are prefixed with 'wizard-'
        assert 'id="wizard-next-btn"' in body
        assert 'data-disabled="1"' in body or 'aria-disabled="true"' in body
    finally:
        # Cleanup
        with contextlib.suppress(FileNotFoundError):
            md_path.unlink()
        with contextlib.suppress(OSError):
            # Directory not empty or other issue; ignore in tests
            test_server_dir.rmdir()
