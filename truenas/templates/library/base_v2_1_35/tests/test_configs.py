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


def test_add_duplicate_config_with_different_data(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.configs.add("test_config", "test_data", "/some/path")
    with pytest.raises(Exception):
        c1.configs.add("test_config", "test_data2", "/some/path")


def test_add_config_with_empty_target(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.configs.add("test_config", "test_data", "")


def test_add_duplicate_target(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.configs.add("test_config", "test_data", "/some/path")
    with pytest.raises(Exception):
        c1.configs.add("test_config2", "test_data2", "/some/path")


def test_add_config(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.configs.add("test_config", "$test_data", "/some/path")
    output = render.render()
    assert output["configs"]["test_config"]["content"] == "$$test_data"
    assert output["services"]["test_container"]["configs"] == [{"source": "test_config", "target": "/some/path"}]


def test_add_config_with_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.configs.add("test_config", "test_data", "/some/path", "0777")
    output = render.render()
    assert output["configs"]["test_config"]["content"] == "test_data"
    assert output["services"]["test_container"]["configs"] == [
        {"source": "test_config", "target": "/some/path", "mode": 511}
    ]
