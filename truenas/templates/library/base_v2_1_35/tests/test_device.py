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


def test_add_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.devices.add_device("/h/dev/sda", "/c/dev/sda")
    c1.devices.add_device("/h/dev/sdb", "/c/dev/sdb", "rwm")
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/h/dev/sda:/c/dev/sda", "/h/dev/sdb:/c/dev/sdb:rwm"]


def test_devices_without_host(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("", "/c/dev/sda")


def test_devices_without_container(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("/h/dev/sda", "")


def test_add_duplicate_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.devices.add_device("/h/dev/sda", "/c/dev/sda")
    with pytest.raises(Exception):
        c1.devices.add_device("/h/dev/sda", "/c/dev/sda")


def test_add_device_with_invalid_container_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("/h/dev/sda", "c/dev/sda")


def test_add_device_with_invalid_host_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("h/dev/sda", "/c/dev/sda")


def test_add_disallowed_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("/dev/dri", "/c/dev/sda")


def test_add_device_with_invalid_cgroup_perm(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("/h/dev/sda", "/c/dev/sda", "invalid")


def test_automatically_add_gpu_devices(mock_values):
    mock_values["resources"] = {"gpus": {"use_all_gpus": True}}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/dev/dri:/dev/dri"]
    assert output["services"]["test_container"]["group_add"] == [44, 107, 568]


def test_automatically_add_gpu_devices_and_kfd(mock_values):
    mock_values["resources"] = {"gpus": {"use_all_gpus": True, "kfd_device_exists": True}}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/dev/dri:/dev/dri", "/dev/kfd:/dev/kfd"]
    assert output["services"]["test_container"]["group_add"] == [44, 107, 568]


def test_remove_gpu_devices(mock_values):
    mock_values["resources"] = {"gpus": {"use_all_gpus": True}}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.devices.remove_devices()
    output = render.render()
    assert "devices" not in output["services"]["test_container"]
    assert output["services"]["test_container"]["group_add"] == [568]


def test_add_usb_bus(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.devices.add_usb_bus()
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/dev/bus/usb:/dev/bus/usb"]


def test_add_usb_bus_disallowed(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.devices.add_device("/dev/bus/usb", "/dev/bus/usb")


def test_add_snd_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_snd_device()
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/dev/snd:/dev/snd"]
    assert output["services"]["test_container"]["group_add"] == [29, 568]


def test_add_tun_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_tun_device()
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/dev/net/tun:/dev/net/tun"]
