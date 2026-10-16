import pytest
from sqlalchemy.exc import IntegrityError

from app.models import WizardStep


def test_unique_server_position_constraint(session):
    """(server_type, category, position) must be unique."""
    # Both steps must have same category to test the unique constraint
    a = WizardStep(server_type="plex", category="post_invite", position=1, markdown="a")
    b = WizardStep(server_type="plex", category="post_invite", position=1, markdown="b")

    session.add(a)
    session.commit()

    session.add(b)
    with pytest.raises(IntegrityError):
        session.commit()  # duplicate (server_type, category, position)
