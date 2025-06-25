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


def test_auto_add_vars(mock_values):
    mock_values["TZ"] = "Etc/UTC"
    mock_values["run_as"] = {"user": "1000", "group": "1000"}
    mock_values["resources"] = {
        "gpus": {
            "nvidia_gpu_selection": {
                "pci_slot_0": {"uuid": "uuid_0", "use_gpu": True},
                "pci_slot_1": {"uuid": "uuid_1", "use_gpu": True},
            },
        }
    }

    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    envs = output["services"]["test_container"]["environment"]
    assert len(envs) == 11
    assert envs["TZ"] == "Etc/UTC"
    assert envs["PUID"] == "1000"
    assert envs["UID"] == "1000"
    assert envs["USER_ID"] == "1000"
    assert envs["PGID"] == "1000"
    assert envs["GID"] == "1000"
    assert envs["GROUP_ID"] == "1000"
    assert envs["UMASK"] == "002"
    assert envs["UMASK_SET"] == "002"
    assert envs["NVIDIA_DRIVER_CAPABILITIES"] == "all"
    assert envs["NVIDIA_VISIBLE_DEVICES"] == "uuid_0,uuid_1"


def test_skip_generic_variables(mock_values):
    mock_values["skip_generic_variables"] = True
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    envs = output["services"]["test_container"]["environment"]

    assert len(envs) == 1
    assert envs["NVIDIA_VISIBLE_DEVICES"] == "void"


def test_add_from_all_sources(mock_values):
    mock_values["TZ"] = "Etc/UTC"
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_env("APP_ENV", "test_value")
    c1.environment.add_user_envs(
        [
            {"name": "USER_ENV", "value": "test_value2"},
        ]
    )
    output = render.render()
    envs = output["services"]["test_container"]["environment"]
    assert envs["APP_ENV"] == "test_value"
    assert envs["USER_ENV"] == "test_value2"
    assert envs["TZ"] == "Etc/UTC"


def test_user_add_vars(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_user_envs(
        [
            {"name": "MY_ENV", "value": "test_value"},
            {"name": "MY_ENV2", "value": "test_value2"},
        ]
    )
    output = render.render()
    envs = output["services"]["test_container"]["environment"]
    assert envs["MY_ENV"] == "test_value"
    assert envs["MY_ENV2"] == "test_value2"


def test_user_add_duplicate_vars(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.environment.add_user_envs(
            [
                {"name": "MY_ENV", "value": "test_value"},
                {"name": "MY_ENV", "value": "test_value2"},
            ]
        )


def test_user_env_without_name(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.environment.add_user_envs(
            [
                {"name": "", "value": "test_value"},
            ]
        )


def test_user_env_try_to_overwrite_auto_vars(mock_values):
    mock_values["TZ"] = "Etc/UTC"
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_user_envs(
        [
            {"name": "TZ", "value": "test_value"},
        ]
    )
    with pytest.raises(Exception):
        render.render()


def test_user_env_try_to_overwrite_app_dev_vars(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_user_envs(
        [
            {"name": "PORT", "value": "test_value"},
        ]
    )
    c1.environment.add_env("PORT", "test_value2")
    with pytest.raises(Exception):
        render.render()


def test_app_dev_vars_try_to_overwrite_auto_vars(mock_values):
    mock_values["TZ"] = "Etc/UTC"
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_env("TZ", "test_value")
    with pytest.raises(Exception):
        render.render()


def test_app_dev_no_name(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.environment.add_env("", "test_value")


def test_app_dev_duplicate_vars(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_env("PORT", "test_value")
    with pytest.raises(Exception):
        c1.environment.add_env("PORT", "test_value2")


def test_format_vars(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.environment.add_env("APP_ENV", "test_$value")
    c1.environment.add_env("APP_ENV_BOOL", True)
    c1.environment.add_env("APP_ENV_INT", 10)
    c1.environment.add_env("APP_ENV_FLOAT", 10.5)
    c1.environment.add_user_envs(
        [
            {"name": "USER_ENV", "value": "test_$value2"},
        ]
    )

    output = render.render()
    envs = output["services"]["test_container"]["environment"]
    assert envs["APP_ENV"] == "test_$$value"
    assert envs["USER_ENV"] == "test_$$value2"
    assert envs["APP_ENV_BOOL"] == "true"
    assert envs["APP_ENV_INT"] == "10"
    assert envs["APP_ENV_FLOAT"] == "10.5"
