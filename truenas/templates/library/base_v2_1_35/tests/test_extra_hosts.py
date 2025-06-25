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


def test_add_extra_host(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_extra_host("test_host", "127.0.0.1")
    c1.add_extra_host("test_host2", "127.0.0.2")
    c1.add_extra_host("host.docker.internal", "host-gateway")
    output = render.render()
    assert output["services"]["test_container"]["extra_hosts"] == {
        "host.docker.internal": "host-gateway",
        "test_host": "127.0.0.1",
        "test_host2": "127.0.0.2",
    }


def test_add_duplicate_extra_host(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_extra_host("test_host", "127.0.0.1")
    with pytest.raises(Exception):
        c1.add_extra_host("test_host", "127.0.0.2")


def test_add_extra_host_with_ipv6(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_extra_host("test_host", "::1")
    output = render.render()
    assert output["services"]["test_container"]["extra_hosts"] == {"test_host": "::1"}


def test_add_extra_host_with_invalid_ip(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_extra_host("test_host", "invalid_ip")
