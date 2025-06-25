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


def test_empty_container_name(mock_values):
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("  ", "test_image")


def test_resolve_image(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["image"] == "nginx:latest"


def test_missing_repo(mock_values):
    mock_values["images"]["test_image"]["repository"] = ""
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("test_container", "test_image")


def test_missing_tag(mock_values):
    mock_values["images"]["test_image"]["tag"] = ""
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("test_container", "test_image")


def test_non_existing_image(mock_values):
    render = Render(mock_values)
    with pytest.raises(Exception):
        render.add_container("test_container", "non_existing_image")


def test_pull_policy(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_pull_policy("always")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["pull_policy"] == "always"


def test_invalid_pull_policy(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    with pytest.raises(Exception):
        c1.set_pull_policy("invalid_policy")


def test_clear_caps(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.add_caps(["NET_ADMIN"])
    c1.clear_caps()
    c1.healthcheck.disable()
    output = render.render()
    assert "cap_drop" not in output["services"]["test_container"]
    assert "cap_add" not in output["services"]["test_container"]


def test_privileged(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_privileged(True)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["privileged"] is True


def test_tty(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_tty(True)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["tty"] is True


def test_init(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_init(True)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["init"] is True


def test_read_only(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_read_only(True)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["read_only"] is True


def test_stdin(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_stdin(True)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["stdin_open"] is True


def test_hostname(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_hostname("test_hostname")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["hostname"] == "test_hostname"


def test_grace_period(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_grace_period(10)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["stop_grace_period"] == "10s"


def test_user(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_user(1000, 1000)
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["user"] == "1000:1000"


def test_invalid_user(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.set_user(-100, 1000)


def test_add_group(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_group(1000)
    c1.add_group("video")
    output = render.render()
    assert output["services"]["test_container"]["group_add"] == [568, 1000, "video"]


def test_add_duplicate_group(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_group(1000)
    with pytest.raises(Exception):
        c1.add_group(1000)


def test_add_group_as_string(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_group("1000")


def test_add_docker_socket(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_docker_socket()
    output = render.render()
    assert output["services"]["test_container"]["group_add"] == [568, 999]
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/var/run/docker.sock",
            "target": "/var/run/docker.sock",
            "read_only": True,
            "bind": {
                "propagation": "rprivate",
                "create_host_path": False,
            },
        }
    ]


def test_snd_device(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_snd_device()
    output = render.render()
    assert output["services"]["test_container"]["devices"] == ["/dev/snd:/dev/snd"]
    assert output["services"]["test_container"]["group_add"] == [29, 568]


def test_shm_size(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_shm_size_mb(10)
    output = render.render()
    assert output["services"]["test_container"]["shm_size"] == "10M"


def test_valid_caps(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_caps(["ALL", "NET_ADMIN"])
    output = render.render()
    assert output["services"]["test_container"]["cap_add"] == ["ALL", "NET_ADMIN"]
    assert output["services"]["test_container"]["cap_drop"] == ["ALL"]


def test_add_duplicate_caps(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_caps(["ALL", "NET_ADMIN", "NET_ADMIN"])


def test_invalid_caps(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_caps(["invalid_cap"])


def test_network_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_network_mode("host")
    output = render.render()
    assert output["services"]["test_container"]["network_mode"] == "host"


def test_auto_network_mode_with_host_network(mock_values):
    mock_values["network"] = {"host_network": True}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["network_mode"] == "host"


def test_network_mode_with_container(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_network_mode("service:test_container")
    output = render.render()
    assert output["services"]["test_container"]["network_mode"] == "service:test_container"


def test_network_mode_with_container_missing(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.set_network_mode("service:missing_container")


def test_invalid_network_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.set_network_mode("invalid_mode")


def test_entrypoint(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_entrypoint(["/bin/bash", "-c", "echo hello $MY_ENV"])
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["entrypoint"] == ["/bin/bash", "-c", "echo hello $$MY_ENV"]


def test_command(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.set_command(["echo", "hello $MY_ENV"])
    c1.healthcheck.disable()
    output = render.render()
    assert output["services"]["test_container"]["command"] == ["echo", "hello $$MY_ENV"]


def test_add_ports(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_port({"port_number": 8081, "container_port": 8080, "bind_mode": "published"})
    c1.add_port({"port_number": 8082, "container_port": 8080, "bind_mode": "published", "protocol": "udp"})
    c1.add_port({"port_number": 8083, "container_port": 8080, "bind_mode": "exposed"})
    c1.add_port({"port_number": 8084, "container_port": 8080, "bind_mode": ""})
    c1.add_port(
        {"port_number": 9091, "container_port": 9091, "bind_mode": "published"},
        {"container_port": 9092, "protocol": "udp"},
    )
    output = render.render()
    assert output["services"]["test_container"]["ports"] == [
        {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress"},
        {"published": 8082, "target": 8080, "protocol": "udp", "mode": "ingress"},
        {"published": 9091, "target": 9092, "protocol": "udp", "mode": "ingress"},
    ]
    assert output["services"]["test_container"]["expose"] == ["8080/tcp"]


def test_add_ports_with_invalid_host_ips(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_port({"port_number": 8081, "container_port": 8080, "bind_mode": "published", "host_ips": "invalid"})


def test_add_ports_with_empty_host_ips(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_port({"port_number": 8081, "container_port": 8080, "bind_mode": "published", "host_ips": []})
    output = render.render()
    assert output["services"]["test_container"]["ports"] == [
        {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress"}
    ]


def test_set_ipc_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_ipc_mode("host")
    output = render.render()
    assert output["services"]["test_container"]["ipc"] == "host"


def test_set_ipc_empty_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_ipc_mode("")
    output = render.render()
    assert output["services"]["test_container"]["ipc"] == ""


def test_set_ipc_mode_with_invalid_ipc_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.set_ipc_mode("invalid")


def test_set_ipc_mode_with_container_ipc_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c2 = render.add_container("test_container2", "test_image")
    c2.healthcheck.disable()
    c1.set_ipc_mode("container:test_container2")
    output = render.render()
    assert output["services"]["test_container"]["ipc"] == "container:test_container2"


def test_set_ipc_mode_with_container_ipc_mode_and_invalid_container(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.set_ipc_mode("container:invalid")


def test_set_cgroup(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.set_cgroup("host")
    output = render.render()
    assert output["services"]["test_container"]["cgroup"] == "host"


def test_set_cgroup_invalid(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.set_cgroup("invalid")
