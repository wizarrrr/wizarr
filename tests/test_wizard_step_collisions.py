"""Tests for wizard step position collisions (issue #1288).

A step position is unique per (server_type, category). An edit or a reorder
that collides with that constraint must not give a 500, and the next request
must still work.
"""

import json

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import InternalServerError

from app.blueprints.wizard_admin import routes as wizard_admin_routes
from app.extensions import db
from app.models import (
    MediaServer,
    WizardBundle,
    WizardBundleStep,
    WizardStep,
)
from app.settings_cache import clear_settings_cache

CONFLICT_MESSAGE = "Cannot save the change because it conflicts"


@pytest.fixture
def steps(session):
    """Create a Plex step and a Jellyfin step at the same position."""
    session.add(
        MediaServer(name="Plex", server_type="plex", url="http://p", api_key="k")
    )
    plex = WizardStep(
        server_type="plex", category="post_invite", position=0, markdown="# Plex"
    )
    jellyfin = WizardStep(
        server_type="jellyfin", category="post_invite", position=0, markdown="# Jf"
    )
    session.add_all([plex, jellyfin])
    session.commit()
    return {"plex": plex.id, "jellyfin": jellyfin.id}


def _edit_to_plex(client, step_id: int):
    return client.post(
        f"/settings/wizard/{step_id}/edit",
        data={
            "server_type": "plex",
            "category": "post_invite",
            "title": "Moved",
            "markdown": "# Moved",
        },
        headers={"HX-Request": "true"},
    )


def test_edit_into_other_group_moves_step_to_free_position(admin_client, steps):
    response = _edit_to_plex(admin_client, steps["jellyfin"])

    assert response.status_code == 200
    assert CONFLICT_MESSAGE not in response.get_data(as_text=True)
    db.session.expire_all()
    moved = db.session.get(WizardStep, steps["jellyfin"])
    assert moved is not None
    assert (moved.server_type, moved.category, moved.position) == (
        "plex",
        "post_invite",
        1,
    )

    later = admin_client.get("/settings/wizard/", headers={"HX-Request": "true"})
    assert later.status_code == 200


def test_edit_that_collides_shows_error_and_next_request_works(
    admin_client, steps, monkeypatch
):
    # Make the edit write a position that the Plex step already holds.
    monkeypatch.setattr(wizard_admin_routes, "_next_free_position", lambda *_: 0)

    response = _edit_to_plex(admin_client, steps["jellyfin"])

    assert response.status_code == 200
    assert CONFLICT_MESSAGE in response.get_data(as_text=True)
    db.session.expire_all()
    unchanged = db.session.get(WizardStep, steps["jellyfin"])
    assert unchanged is not None
    assert unchanged.server_type == "jellyfin"

    later = admin_client.get("/settings/wizard/", headers={"HX-Request": "true"})
    assert later.status_code == 200
    assert CONFLICT_MESSAGE not in later.get_data(as_text=True)


def test_reorder_skips_duplicates_and_keeps_unlisted_steps(admin_client, session):
    rows = [
        WizardStep(server_type="plex", category="pre_invite", position=i, markdown="x")
        for i in range(3)
    ]
    session.add_all(rows)
    session.commit()
    a, b, c = (r.id for r in rows)

    response = admin_client.post(
        "/settings/wizard/reorder",
        data=json.dumps(
            {"server_type": "plex", "category": "pre_invite", "order": [c, c, a]}
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    db.session.expire_all()
    ordered = (
        WizardStep.query.filter_by(server_type="plex", category="pre_invite")
        .order_by(WizardStep.position)
        .all()
    )
    assert [(s.id, s.position) for s in ordered] == [(c, 0), (a, 1), (b, 2)]


def test_reorder_bundle_moves_step_after_step_at_position_zero(admin_client, session):
    post = WizardStep(
        server_type="custom", category="post_invite", position=0, markdown="x"
    )
    pre = WizardStep(
        server_type="custom", category="pre_invite", position=0, markdown="y"
    )
    bundle = WizardBundle(name="Bundle")
    session.add_all([post, pre, bundle])
    session.flush()
    session.add_all(
        [
            WizardBundleStep(bundle_id=bundle.id, step_id=post.id, position=0),
            WizardBundleStep(bundle_id=bundle.id, step_id=pre.id, position=1),
        ]
    )
    session.commit()

    response = admin_client.post(
        f"/settings/wizard/bundle/{bundle.id}/reorder",
        data=json.dumps(
            {
                "order": [
                    {"id": post.id, "category": None},
                    {"id": pre.id, "category": "post_invite"},
                ]
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    db.session.expire_all()
    moved = db.session.get(WizardStep, pre.id)
    assert moved is not None
    assert (moved.category, moved.position) == ("post_invite", 1)


def test_error_500_handler_rolls_back_failed_session(app, session):
    handler = app.error_handler_spec[None][500][InternalServerError]
    with app.test_request_context("/"):
        db.session.add_all(
            [
                WizardStep(
                    server_type="x", category="pre_invite", position=0, markdown="a"
                ),
                WizardStep(
                    server_type="x", category="pre_invite", position=0, markdown="b"
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        # Make the context processor query the database during the render.
        clear_settings_cache()

        body, status = handler(InternalServerError())

        assert status == 500
        assert body
        assert db.session.execute(db.text("SELECT 1")).scalar() == 1
