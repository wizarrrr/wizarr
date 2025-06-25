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


def test_add_sysctl(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.sysctls.add("net.ipv4.ip_forward", 1)
    c1.sysctls.add("fs.mqueue.msg_max", 100)
    output = render.render()
    assert output["services"]["test_container"]["sysctls"] == {"net.ipv4.ip_forward": "1", "fs.mqueue.msg_max": "100"}


def test_add_net_sysctl_with_host_network(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_network_mode("host")
    c1.sysctls.add("net.ipv4.ip_forward", 1)
    with pytest.raises(Exception):
        render.render()


def test_add_duplicate_sysctl(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.sysctls.add("net.ipv4.ip_forward", 1)
    with pytest.raises(Exception):
        c1.sysctls.add("net.ipv4.ip_forward", 0)


def test_add_empty_sysctl(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.sysctls.add("", 1)


def test_add_sysctl_with_invalid_key(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.sysctls.add("invalid.sysctl", 1)
    with pytest.raises(Exception):
        render.render()
