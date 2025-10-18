import pytest

from app.extensions import db
from app.models import MediaServer, WizardStep


@pytest.fixture
def preview_step_factory(app):
    created_types: list[str] = []

    def _create(
        server_type: str, *, pre_steps: list[str], post_steps: list[str]
    ) -> None:
        with app.app_context():
            db.session.query(WizardStep).filter_by(server_type=server_type).delete()
            db.session.query(MediaServer).filter_by(server_type=server_type).delete()
            db.session.commit()

            server = MediaServer(
                name=f"{server_type.title()} Preview Server",
                server_type=server_type,
                url=f"http://{server_type}.preview.local",
                api_key=f"api-{server_type}",
            )
            db.session.add(server)
            db.session.flush()

            for position, content in enumerate(pre_steps):
                db.session.add(
                    WizardStep(
                        server_type=server_type,
                        category="pre_invite",
                        position=position,
                        markdown=f"# Pre {position + 1}\n\n{content}",
                    )
                )

            for position, content in enumerate(post_steps):
                db.session.add(
                    WizardStep(
                        server_type=server_type,
                        category="post_invite",
                        position=position,
                        markdown=f"# Post {position + 1}\n\n{content}",
                    )
                )

            db.session.commit()

        created_types.append(server_type)

    yield _create

    with app.app_context():
        for server_type in created_types:
            db.session.query(WizardStep).filter_by(server_type=server_type).delete()
            db.session.query(MediaServer).filter_by(server_type=server_type).delete()
        db.session.commit()


@pytest.fixture
def enable_wizard_preview(client):
    with client.session_transaction() as sess:
        sess["wizard_access"] = "preview-test"
    return


@pytest.mark.parametrize("server_type", ["plex", "jellyfin", "emby", "audiobookshelf"])
def test_preview_renders_pre_then_post_steps(
    client, preview_step_factory, enable_wizard_preview, server_type
):
    preview_step_factory(
        server_type,
        pre_steps=[f"{server_type} pre step"],
        post_steps=[f"{server_type} post step"],
    )

    response = client.get(f"/wizard/{server_type}/0")
    assert response.status_code == 200
    body = response.data.decode()

    assert f"{server_type} pre step" in body
    assert f"{server_type} post step" not in body
    assert "Step 1 of 2" in body


def test_preview_navigation_crosses_pre_and_post_categories(
    client, preview_step_factory, enable_wizard_preview
):
    preview_step_factory(
        "plex",
        pre_steps=["first pre", "second pre"],
        post_steps=["first post", "second post"],
    )

    # Initial request should show the very first pre-invite step
    initial = client.get("/wizard/plex/0")
    assert initial.status_code == 200
    initial_body = initial.data.decode()
    assert "first pre" in initial_body
    assert "Step 1 of 4" in initial_body

    # HTMX request to the second step should still be pre-invite content
    second = client.get(
        "/wizard/plex/1",
        query_string={"dir": "next"},
        headers={"HX-Request": "true"},
    )
    assert second.status_code == 200
    assert "second pre" in second.data.decode()
    assert second.headers.get("X-Wizard-Idx") == "1"
    assert second.headers.get("X-Wizard-Step-Phase") == "pre"

    # Next step after pre-invite list should be the first post-invite step
    third = client.get(
        "/wizard/plex/2",
        query_string={"dir": "next"},
        headers={"HX-Request": "true"},
    )
    assert third.status_code == 200
    assert "first post" in third.data.decode()
    assert third.headers.get("X-Wizard-Idx") == "2"
    assert third.headers.get("X-Wizard-Step-Phase") == "post"
