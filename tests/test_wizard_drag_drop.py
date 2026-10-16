"""
Tests for wizard step drag-and-drop functionality.

This module tests the drag-and-drop reordering of wizard steps, including:
- Reordering within the same category
- Moving steps between categories (pre-invite ↔ post-invite)
- Preventing moves between different server types
- Error handling
"""

import json

import pytest

from app.extensions import db
from app.models import WizardStep


@pytest.fixture
def wizard_steps(session):
    """Create test wizard steps for drag-and-drop testing."""
    steps = [
        # Plex pre-invite steps
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=0,
            title="Plex Pre Step 1",
            markdown="# Pre Step 1",
        ),
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=1,
            title="Plex Pre Step 2",
            markdown="# Pre Step 2",
        ),
        WizardStep(
            server_type="plex",
            category="pre_invite",
            position=2,
            title="Plex Pre Step 3",
            markdown="# Pre Step 3",
        ),
        # Plex post-invite steps
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            title="Plex Post Step 1",
            markdown="# Post Step 1",
        ),
        WizardStep(
            server_type="plex",
            category="post_invite",
            position=1,
            title="Plex Post Step 2",
            markdown="# Post Step 2",
        ),
        # Jellyfin pre-invite steps
        WizardStep(
            server_type="jellyfin",
            category="pre_invite",
            position=0,
            title="Jellyfin Pre Step 1",
            markdown="# Jellyfin Pre",
        ),
    ]

    session.add_all(steps)
    session.commit()

    # Return step IDs for testing
    return {
        "plex_pre": [s.id for s in steps[:3]],
        "plex_post": [s.id for s in steps[3:5]],
        "jellyfin_pre": [steps[5].id],
    }


def _reorder(client, server_type: str, category: str, order: list[int]):
    return client.post(
        "/settings/wizard/reorder",
        data=json.dumps(
            {"server_type": server_type, "category": category, "order": order}
        ),
        content_type="application/json",
    )


def _ordered_steps(server_type: str, category: str) -> list[WizardStep]:
    return (
        WizardStep.query.filter_by(server_type=server_type, category=category)
        .order_by(WizardStep.position)
        .all()
    )


class TestDragDropReordering:
    """Test drag-and-drop reordering functionality."""

    def test_reorder_within_same_category(self, admin_client, wizard_steps):
        new_order = list(reversed(wizard_steps["plex_pre"]))

        response = _reorder(admin_client, "plex", "pre_invite", new_order)

        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"
        steps = _ordered_steps("plex", "pre_invite")
        assert [s.id for s in steps] == new_order
        assert [s.position for s in steps] == [0, 1, 2]

    def test_move_step_between_categories(self, admin_client, wizard_steps):
        step_id = wizard_steps["plex_pre"][0]
        new_order = wizard_steps["plex_post"] + [step_id]

        response = _reorder(admin_client, "plex", "post_invite", new_order)

        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"

        step = db.session.get(WizardStep, step_id)
        assert step is not None
        assert step.category == "post_invite"
        assert step.position == 2  # Last position in new category

        pre_steps = _ordered_steps("plex", "pre_invite")
        assert len(pre_steps) == 2
        assert step_id not in [s.id for s in pre_steps]

    @pytest.mark.parametrize(
        ("payload", "content_type", "status"),
        [
            (
                json.dumps(
                    {"server_type": "plex", "category": "invalid", "order": [1]}
                ),
                "application/json",
                400,
            ),
            (
                json.dumps({"server_type": "plex", "order": [1]}),
                "application/json",
                400,
            ),
            ("invalid json", "application/json", 400),
            (
                "server_type=plex&category=pre_invite",
                "application/x-www-form-urlencoded",
                415,
            ),
        ],
        ids=["invalid-category", "missing-category", "invalid-json", "not-json"],
    )
    def test_reorder_rejects_bad_request(
        self, admin_client, wizard_steps, payload, content_type, status
    ):
        response = admin_client.post(
            "/settings/wizard/reorder", data=payload, content_type=content_type
        )

        assert response.status_code == status
        assert [s.id for s in _ordered_steps("plex", "pre_invite")] == wizard_steps[
            "plex_pre"
        ]

    def test_reorder_requires_authentication(self, client, wizard_steps):
        response = _reorder(
            client, "plex", "pre_invite", list(reversed(wizard_steps["plex_pre"]))
        )

        assert response.status_code == 302
        assert "/login" in response.location
        assert [s.id for s in _ordered_steps("plex", "pre_invite")] == wizard_steps[
            "plex_pre"
        ]

    def test_reorder_preserves_other_categories(self, admin_client, wizard_steps):
        original_post_ids = wizard_steps["plex_post"]

        response = _reorder(
            admin_client, "plex", "pre_invite", list(reversed(wizard_steps["plex_pre"]))
        )

        assert response.status_code == 200
        post_steps = _ordered_steps("plex", "post_invite")
        assert [s.id for s in post_steps] == original_post_ids
        assert [s.position for s in post_steps] == [0, 1]

    def test_reorder_preserves_other_servers(self, admin_client, wizard_steps):
        jellyfin_id = wizard_steps["jellyfin_pre"][0]

        response = _reorder(
            admin_client, "plex", "pre_invite", list(reversed(wizard_steps["plex_pre"]))
        )

        assert response.status_code == 200
        jellyfin_step = db.session.get(WizardStep, jellyfin_id)
        assert jellyfin_step is not None
        assert jellyfin_step.server_type == "jellyfin"
        assert jellyfin_step.category == "pre_invite"
        assert jellyfin_step.position == 0


class TestDragDropEdgeCases:
    """Test edge cases and error scenarios for drag-and-drop."""

    def test_reorder_empty_list(self, admin_client):
        response = _reorder(admin_client, "plex", "pre_invite", [])

        # Should succeed (no-op)
        assert response.status_code == 200

    def test_reorder_single_step(self, admin_client, wizard_steps):
        jellyfin_id = wizard_steps["jellyfin_pre"][0]

        response = _reorder(admin_client, "jellyfin", "pre_invite", [jellyfin_id])

        assert response.status_code == 200
        step = db.session.get(WizardStep, jellyfin_id)
        assert step is not None
        assert step.position == 0

    def test_reorder_with_nonexistent_step_id(self, admin_client, wizard_steps):
        plex_pre_ids = wizard_steps["plex_pre"]

        response = _reorder(admin_client, "plex", "pre_invite", plex_pre_ids + [99999])

        # Should succeed but ignore non-existent ID
        assert response.status_code == 200
        steps = _ordered_steps("plex", "pre_invite")
        assert len(steps) == 3
        assert all(s.id in plex_pre_ids for s in steps)
