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


def test_device_cgroup_rule(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_device_cgroup_rule("c 13:* rwm")
    c1.add_device_cgroup_rule("b 10:20 rwm")
    output = render.render()
    assert output["services"]["test_container"]["device_cgroup_rules"] == [
        "b 10:20 rwm",
        "c 13:* rwm",
    ]


def test_device_cgroup_rule_duplicate(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_device_cgroup_rule("c 13:* rwm")
    with pytest.raises(Exception):
        c1.add_device_cgroup_rule("c 13:* rwm")


def test_device_cgroup_rule_duplicate_group(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_device_cgroup_rule("c 13:* rwm")
    with pytest.raises(Exception):
        c1.add_device_cgroup_rule("c 13:* rm")


def test_device_cgroup_rule_invalid_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_device_cgroup_rule("d 10:20 rwm")


def test_device_cgroup_rule_invalid_perm(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_device_cgroup_rule("a 10:20 rwd")


def test_device_cgroup_rule_invalid_format(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_device_cgroup_rule("a 10 20 rwd")


def test_device_cgroup_rule_invalid_format_missing_major(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_device_cgroup_rule("a 10 rwd")
