import pytest


from render import Render


@pytest.fixture
def mock_values():
    return {
        "ix_context": {
            "app_metadata": {
                "name": "test_app",
                "title": "Test App",
                "train": "enterprise",
            }
        },
        "images": {
            "test_image": {
                "repository": "nginx",
                "tag": "latest",
            }
        },
    }


def test_notes(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert (
        output["x-notes"]
        == """# Test App

## Security

### Container: [test_container]

- Is running as unknown user
- Is running as unknown group

## Bug Reports and Feature Requests

If you find a bug in this app or have an idea for a new feature, please file an issue at
https://ixsystems.atlassian.net

"""
    )


def test_notes_on_non_enterprise_train(mock_values):
    mock_values["ix_context"]["app_metadata"]["train"] = "community"
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_user(568, 568)
    c1.healthcheck.disable()
    output = render.render()
    assert (
        output["x-notes"]
        == """# Test App

## Bug Reports and Feature Requests

If you find a bug in this app or have an idea for a new feature, please file an issue at
https://github.com/truenas/apps

"""
    )


def test_notes_with_warnings(mock_values):
    render = Render(mock_values)
    render.notes.add_warning("this is not properly configured. fix it now!")
    render.notes.add_warning("that is not properly configured. fix it later!")
    c1 = render.add_container("test_container", "test_image")
    c1.set_user(568, 568)
    c1.healthcheck.disable()
    output = render.render()
    assert (
        output["x-notes"]
        == """# Test App

## Warnings

- this is not properly configured. fix it now!
- that is not properly configured. fix it later!

## Bug Reports and Feature Requests

If you find a bug in this app or have an idea for a new feature, please file an issue at
https://ixsystems.atlassian.net

"""
    )


def test_notes_with_deprecations(mock_values):
    render = Render(mock_values)
    render.notes.add_deprecation("this is will be removed later. fix it now!")
    render.notes.add_deprecation("that is will be removed later. fix it later!")
    c1 = render.add_container("test_container", "test_image")
    c1.set_user(568, 568)
    c1.healthcheck.disable()
    output = render.render()
    assert (
        output["x-notes"]
        == """# Test App

## Deprecations

- this is will be removed later. fix it now!
- that is will be removed later. fix it later!

## Bug Reports and Feature Requests

If you find a bug in this app or have an idea for a new feature, please file an issue at
https://ixsystems.atlassian.net

"""
    )


def test_notes_with_body(mock_values):
    render = Render(mock_values)
    render.notes.set_body(
        """## Additional info

Some info
some other info.
"""
    )
    c1 = render.add_container("test_container", "test_image")
    c1.set_user(568, 568)
    c1.healthcheck.disable()
    output = render.render()
    assert (
        output["x-notes"]
        == """# Test App

## Additional info

Some info
some other info.

## Bug Reports and Feature Requests

If you find a bug in this app or have an idea for a new feature, please file an issue at
https://ixsystems.atlassian.net

"""
    )


def test_notes_all(mock_values):
    render = Render(mock_values)
    render.notes.add_warning("this is not properly configured. fix it now!")
    render.notes.add_warning("that is not properly configured. fix it later!")
    render.notes.add_deprecation("this is will be removed later. fix it now!")
    render.notes.add_deprecation("that is will be removed later. fix it later!")
    render.notes.set_body(
        """## Additional info

Some info
some other info.
"""
    )
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_privileged(True)
    c1.set_user(0, 0)
    c1.set_ipc_mode("host")
    c1.set_cgroup("host")
    c1.set_tty(True)
    c1.remove_security_opt("no-new-privileges")
    c1.restart.set_policy("on-failure", 1)

    c2 = render.add_container("test_container2", "test_image")
    c2.healthcheck.disable()
    c2.set_user(568, 568)

    output = render.render()
    assert (
        output["x-notes"]
        == """# Test App

## Warnings

- Container [test_container] is running with a TTY, Logs will not appear correctly in the UI due to an [upstream bug](https://github.com/docker/docker-py/issues/1394)
- this is not properly configured. fix it now!
- that is not properly configured. fix it later!

## Deprecations

- this is will be removed later. fix it now!
- that is will be removed later. fix it later!

## Security

### Container: [test_container]

**This container is short-lived.**

- Is running with privileged mode enabled
- Is running as root user
- Is running as root group
- Is running with host IPC namespace
- Is running with host cgroup namespace
- Is running without [no-new-privileges] security option

## Additional info

Some info
some other info.

## Bug Reports and Feature Requests

If you find a bug in this app or have an idea for a new feature, please file an issue at
https://ixsystems.atlassian.net

"""  # noqa
    )
