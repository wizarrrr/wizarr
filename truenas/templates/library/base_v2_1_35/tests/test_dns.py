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


def test_auto_add_dns_opts(mock_values):
    mock_values["network"] = {"dns_opts": ["attempts:3", "opt1", "opt2"]}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["dns_opt"] == ["attempts:3", "opt1", "opt2"]


def test_auto_add_dns_searches(mock_values):
    mock_values["network"] = {"dns_searches": ["search1", "search2"]}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["dns_search"] == ["search1", "search2"]


def test_auto_add_dns_nameservers(mock_values):
    mock_values["network"] = {"dns_nameservers": ["nameserver1", "nameserver2"]}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["dns"] == ["nameserver1", "nameserver2"]


def test_add_duplicate_dns_nameservers(mock_values):
    mock_values["network"] = {"dns_nameservers": ["nameserver1", "nameserver1"]}
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("test_container", "test_image")


def test_add_duplicate_dns_searches(mock_values):
    mock_values["network"] = {"dns_searches": ["search1", "search1"]}
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("test_container", "test_image")


def test_add_duplicate_dns_opts(mock_values):
    mock_values["network"] = {"dns_opts": ["attempts:3", "attempts:5"]}
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("test_container", "test_image")
