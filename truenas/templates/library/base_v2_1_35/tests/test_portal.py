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


def test_no_portals(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["x-portals"] == []


def test_add_portal_with_host_ips(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    port1 = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    port2 = {"bind_mode": "published", "port_number": 8081, "host_ips": ["::", "0.0.0.0"]}
    port3 = {"bind_mode": "published", "port_number": 8081, "host_ips": ["1.2.3.4"]}
    port3 = {"bind_mode": "published", "port_number": 8081, "host_ips": ["1.2.3.4"]}
    port4 = {"bind_mode": "exposed", "port_number": 1234, "host_ips": ["1.2.3.4"]}
    render.portals.add(port1)
    render.portals.add(port1, {"name": "test1", "host": "my-host.com"})
    render.portals.add(port2, {"name": "test2"})
    render.portals.add(port3, {"name": "test3", "port": None})
    render.portals.add(port3, {"name": "test4", "port": 1234})
    render.portals.add(port4, {"name": "test5", "port": 1234})
    output = render.render()
    assert output["x-portals"] == [
        {"name": "Web UI", "scheme": "http", "host": "1.2.3.4", "port": 8080, "path": "/"},
        {"name": "test1", "scheme": "http", "host": "my-host.com", "port": 8080, "path": "/"},
        {"name": "test2", "scheme": "http", "host": "0.0.0.0", "port": 8081, "path": "/"},
        {"name": "test3", "scheme": "http", "host": "1.2.3.4", "port": 8081, "path": "/"},
        {"name": "test4", "scheme": "http", "host": "1.2.3.4", "port": 1234, "path": "/"},
    ]


def test_add_duplicate_portal(mock_values):
    render = Render(mock_values)
    port = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    render.portals.add(port)
    with pytest.raises(Exception):
        render.portals.add(port)


def test_add_duplicate_portal_with_explicit_name(mock_values):
    render = Render(mock_values)
    port = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    render.portals.add(port, {"name": "Some Portal"})
    with pytest.raises(Exception):
        render.portals.add(port, {"name": "Some Portal"})


def test_add_portal_with_invalid_scheme(mock_values):
    render = Render(mock_values)
    port = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    with pytest.raises(Exception):
        render.portals.add(port, {"scheme": "invalid_scheme"})


def test_add_portal_with_invalid_path(mock_values):
    render = Render(mock_values)
    port = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    with pytest.raises(Exception):
        render.portals.add(port, {"path": "invalid_path"})


def test_add_portal_with_invalid_path_double_slash(mock_values):
    render = Render(mock_values)
    port = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    with pytest.raises(Exception):
        render.portals.add(port, {"path": "/some//path"})


def test_add_portal_with_invalid_port(mock_values):
    render = Render(mock_values)
    port = {"bind_mode": "published", "port_number": 8080, "host_ips": ["1.2.3.4", "5.6.7.8"]}
    with pytest.raises(Exception):
        render.portals.add(port, {"port": -1})
