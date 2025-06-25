import pytest


from render import Render


@pytest.fixture
def mock_values():
    return {
        "images": {
            "test_image": {
                "repository": "nginx",
                "tag": "latest",
            }
        },
    }


def test_add_dependency(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c2 = render.add_container("test_container2", "test_image")
    c1.healthcheck.disable()
    c2.healthcheck.disable()
    c1.depends.add_dependency("test_container2", "service_started")
    output = render.render()
    assert output["services"]["test_container"]["depends_on"]["test_container2"] == {"condition": "service_started"}


def test_add_dependency_invalid_condition(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    render.add_container("test_container2", "test_image")
    with pytest.raises(Exception):
        c1.depends.add_dependency("test_container2", "invalid_condition")


def test_add_dependency_missing_container(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.depends.add_dependency("test_container2", "service_started")


def test_add_dependency_duplicate(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    render.add_container("test_container2", "test_image")
    c1.depends.add_dependency("test_container2", "service_started")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.depends.add_dependency("test_container2", "service_started")
