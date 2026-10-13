from __future__ import annotations

from app.models import WizardStep


def _enable_wizard_access(client):
    with client.session_transaction() as sess:
        sess["wizard_access"] = "test-code"


def _assert_next_disabled(body: str) -> None:
    # After wizard overhaul, button IDs are prefixed with 'wizard-'
    assert 'id="wizard-next-btn"' in body
    assert 'aria-disabled="true"' in body
    assert 'data-disabled="1"' in body


def test_db_step_requires_interaction_renders_next_disabled(client, session):
    session.add(
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title="Download",
            markdown="# Please download\n[Click me](https://example.com)",
            require_interaction=True,
        )
    )
    session.commit()
    _enable_wizard_access(client)

    # Initial page load (not HTMX) to get full UI chrome with buttons
    resp = client.get("/wizard/plex/0")

    assert resp.status_code == 200
    _assert_next_disabled(resp.data.decode())


def test_file_based_front_matter_require_renders_next_disabled(
    client, session, tmp_path, monkeypatch
):
    # Without DB steps, the wizard reads the markdown files in BASE_DIR.
    monkeypatch.setattr("app.blueprints.wizard.routes.BASE_DIR", tmp_path)
    server_dir = tmp_path / "requiretest"
    server_dir.mkdir()
    (server_dir / "01_test.md").write_text(
        "---\n"
        "title: Require Test\n"
        "require: true\n"
        "---\n\n"
        "# Step\n\n"
        "[Do it](https://example.com)\n",
        encoding="utf-8",
    )
    _enable_wizard_access(client)

    # Initial page load (not HTMX) to get full UI chrome with buttons
    resp = client.get("/wizard/requiretest/0")

    assert resp.status_code == 200
    _assert_next_disabled(resp.data.decode())
