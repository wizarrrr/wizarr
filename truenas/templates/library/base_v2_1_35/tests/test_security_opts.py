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


def test_add_security_opt(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_security_opt("apparmor", "unconfined")
    output = render.render()
    assert output["services"]["test_container"]["security_opt"] == ["apparmor=unconfined", "no-new-privileges=true"]


def test_add_duplicate_security_opt(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_security_opt("no-new-privileges", True)


def test_add_empty_security_opt(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_security_opt("", True)


def test_remove_security_opt(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.remove_security_opt("no-new-privileges")
    output = render.render()
    assert "security_opt" not in output["services"]["test_container"]


def test_add_security_opt_boolean(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.remove_security_opt("no-new-privileges")
    c1.add_security_opt("no-new-privileges", False)
    output = render.render()
    assert output["services"]["test_container"]["security_opt"] == ["no-new-privileges=false"]


def test_add_security_opt_arg(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_security_opt("label", "type", "svirt_apache_t")
    output = render.render()
    assert output["services"]["test_container"]["security_opt"] == [
        "label=type:svirt_apache_t",
        "no-new-privileges=true",
    ]


def test_add_security_opt_with_invalid_opt(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_security_opt("invalid")


def test_add_security_opt_with_opt_containing_value(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.remove_security_opt("no-new-privileges")
    with pytest.raises(Exception):
        c1.add_security_opt("no-new-privileges=true")
    with pytest.raises(Exception):
        c1.add_security_opt("apparmor:unconfined")
