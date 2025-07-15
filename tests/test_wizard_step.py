import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import WizardStep


@pytest.fixture
def session(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        yield db.session
        db.session.rollback()


def test_create_wizard_step(session):
    """Basic insertion & to_dict serialization work."""
    step = WizardStep(
        server_type="plex",
        position=0,
        title="Welcome",
        markdown="# Welcome\nSome intro text",
        requires=["server_url"],
    )
    session.add(step)
    session.commit()

    fetched = WizardStep.query.first()
    assert fetched is not None
    assert fetched.title == "Welcome"
    assert fetched.to_dict() is not None
    assert fetched.to_dict()["server_type"] == "plex"


def test_unique_server_position_constraint(session):
    """(server_type, position) must be unique."""
    a = WizardStep(server_type="plex", position=1, markdown="a")
    b = WizardStep(server_type="plex", position=1, markdown="b")

    session.add(a)
    session.commit()

    session.add(b)
    with pytest.raises(IntegrityError):
        session.commit()  # duplicate position for same server_type
