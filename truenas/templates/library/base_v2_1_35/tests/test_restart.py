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


def test_invalid_restart_policy(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.restart.set_policy("invalid_policy")


def test_valid_restart_policy(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.restart.set_policy("on-failure")
    output = render.render()
    assert output["services"]["test_container"]["restart"] == "on-failure"


def test_valid_restart_policy_with_maximum_retry_count(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.restart.set_policy("on-failure", 10)
    output = render.render()
    assert output["services"]["test_container"]["restart"] == "on-failure:10"


def test_invalid_restart_policy_with_maximum_retry_count(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.restart.set_policy("on-failure", maximum_retry_count=-1)


def test_invalid_restart_policy_with_maximum_retry_count_and_policy(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.restart.set_policy("always", maximum_retry_count=10)
