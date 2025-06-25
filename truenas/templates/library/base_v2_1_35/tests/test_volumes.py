import pytest


from render import Render
from formatter import get_hashed_name_for_volume


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


def test_add_volume_invalid_type(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_storage("/some/path", {"type": "invalid_type"})


def test_add_volume_empty_mount_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.add_storage("", {"type": "tmpfs"})


def test_add_volume_duplicate_mount_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_storage("/some/path", {"type": "tmpfs"})
    with pytest.raises(Exception):
        c1.add_storage("/some/path", {"type": "tmpfs"})


def test_add_volume_host_path_invalid_propagation(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {
        "type": "host_path",
        "host_path_config": {"path": "/mnt/test", "propagation": "invalid_propagation"},
    }
    with pytest.raises(Exception):
        c1.add_storage("/some/path", host_path_config)


def test_add_host_path_volume_no_host_path_config(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path"}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", host_path_config)


def test_add_host_path_volume_no_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"path": ""}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", host_path_config)


def test_add_host_path_with_acl_no_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"acl_enable": True, "acl": {"path": ""}}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", host_path_config)


def test_add_host_path_volume_mount(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"path": "/mnt/test"}}
    c1.add_storage("/some/path", host_path_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/some/path",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_host_path_volume_mount_with_acl(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {
        "type": "host_path",
        "host_path_config": {"path": "/mnt/test", "acl_enable": True, "acl": {"path": "/mnt/test/acl"}},
    }
    c1.add_storage("/some/path", host_path_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test/acl",
            "target": "/some/path",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_host_path_volume_mount_with_propagation(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"path": "/mnt/test", "propagation": "slave"}}
    c1.add_storage("/some/path", host_path_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/some/path",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "slave"},
        }
    ]


def test_add_host_path_volume_mount_with_create_host_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"path": "/mnt/test", "create_host_path": True}}
    c1.add_storage("/some/path", host_path_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/some/path",
            "read_only": False,
            "bind": {"create_host_path": True, "propagation": "rprivate"},
        }
    ]


def test_add_host_path_volume_mount_with_read_only(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "read_only": True, "host_path_config": {"path": "/mnt/test"}}
    c1.add_storage("/some/path", host_path_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/some/path",
            "read_only": True,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_ix_volume_invalid_dataset_name(mock_values):
    mock_values["ix_volumes"] = {"test_dataset": "/mnt/test"}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    ix_volume_config = {"type": "ix_volume", "ix_volume_config": {"dataset_name": "invalid_dataset"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", ix_volume_config)


def test_add_ix_volume_no_ix_volume_config(mock_values):
    mock_values["ix_volumes"] = {"test_dataset": "/mnt/test"}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    ix_volume_config = {"type": "ix_volume"}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", ix_volume_config)


def test_add_ix_volume_volume_mount(mock_values):
    mock_values["ix_volumes"] = {"test_dataset": "/mnt/test"}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    ix_volume_config = {"type": "ix_volume", "ix_volume_config": {"dataset_name": "test_dataset"}}
    c1.add_storage("/some/path", ix_volume_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/some/path",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_ix_volume_volume_mount_with_options(mock_values):
    mock_values["ix_volumes"] = {"test_dataset": "/mnt/test"}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    ix_volume_config = {
        "type": "ix_volume",
        "ix_volume_config": {"dataset_name": "test_dataset", "propagation": "rslave", "create_host_path": True},
    }
    c1.add_storage("/some/path", ix_volume_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/some/path",
            "read_only": False,
            "bind": {"create_host_path": True, "propagation": "rslave"},
        }
    ]


def test_cifs_volume_missing_server(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {"type": "cifs", "cifs_config": {"path": "/path", "username": "user", "password": "password"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_missing_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {"type": "cifs", "cifs_config": {"server": "server", "username": "user", "password": "password"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_missing_username(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {"type": "cifs", "cifs_config": {"server": "server", "path": "/path", "password": "password"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_missing_password(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {"type": "cifs", "cifs_config": {"server": "server", "path": "/path", "username": "user"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_without_cifs_config(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {"type": "cifs"}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_duplicate_option(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {
        "type": "cifs",
        "cifs_config": {
            "server": "server",
            "path": "/path",
            "username": "user",
            "password": "pas$word",
            "options": ["verbose=true", "verbose=true"],
        },
    }
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_disallowed_option(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {
        "type": "cifs",
        "cifs_config": {
            "server": "server",
            "path": "/path",
            "username": "user",
            "password": "pas$word",
            "options": ["user=username"],
        },
    }
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_invalid_options(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {
        "type": "cifs",
        "cifs_config": {
            "server": "server",
            "path": "/path",
            "username": "user",
            "password": "pas$word",
            "options": {"verbose": True},
        },
    }
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_cifs_volume_invalid_options2(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_config = {
        "type": "cifs",
        "cifs_config": {
            "server": "server",
            "path": "/path",
            "username": "user",
            "password": "pas$word",
            "options": [{"verbose": True}],
        },
    }
    with pytest.raises(Exception):
        c1.add_storage("/some/path", cifs_config)


def test_add_cifs_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_inner_config = {"server": "server", "path": "/path", "username": "user", "password": "pas$word"}
    cifs_config = {"type": "cifs", "cifs_config": cifs_inner_config}
    c1.add_storage("/some/path", cifs_config)
    output = render.render()
    vol_name = get_hashed_name_for_volume("cifs", cifs_inner_config)
    assert output["volumes"] == {
        vol_name: {
            "driver_opts": {"type": "cifs", "device": "//server/path", "o": "noperm,password=pas$$word,user=user"}
        }
    }
    assert output["services"]["test_container"]["volumes"] == [
        {"type": "volume", "source": vol_name, "target": "/some/path", "read_only": False, "volume": {"nocopy": False}}
    ]


def test_cifs_volume_with_options(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    cifs_inner_config = {
        "server": "server",
        "path": "/path",
        "username": "user",
        "password": "pas$word",
        "options": ["vers=3.0", "verbose=true"],
    }
    cifs_config = {"type": "cifs", "cifs_config": cifs_inner_config}
    c1.add_storage("/some/path", cifs_config)
    output = render.render()
    vol_name = get_hashed_name_for_volume("cifs", cifs_inner_config)
    assert output["volumes"] == {
        vol_name: {
            "driver_opts": {
                "type": "cifs",
                "device": "//server/path",
                "o": "noperm,password=pas$$word,user=user,verbose=true,vers=3.0",
            }
        }
    }
    assert output["services"]["test_container"]["volumes"] == [
        {"type": "volume", "source": vol_name, "target": "/some/path", "read_only": False, "volume": {"nocopy": False}}
    ]


def test_nfs_volume_missing_server(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {"type": "nfs", "nfs_config": {"path": "/path"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_nfs_volume_missing_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {"type": "nfs", "nfs_config": {"server": "server"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_nfs_volume_without_nfs_config(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {"type": "nfs"}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_nfs_volume_duplicate_option(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {
        "type": "nfs",
        "nfs_config": {"server": "server", "path": "/path", "options": ["verbose=true", "verbose=true"]},
    }
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_nfs_volume_disallowed_option(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {"type": "nfs", "nfs_config": {"server": "server", "path": "/path", "options": ["addr=server"]}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_nfs_volume_invalid_options(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {"type": "nfs", "nfs_config": {"server": "server", "path": "/path", "options": {"verbose": True}}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_nfs_volume_invalid_options2(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_config = {"type": "nfs", "nfs_config": {"server": "server", "path": "/path", "options": [{"verbose": True}]}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", nfs_config)


def test_add_nfs_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_inner_config = {"server": "server", "path": "/path"}
    nfs_config = {"type": "nfs", "nfs_config": nfs_inner_config}
    c1.add_storage("/some/path", nfs_config)
    output = render.render()
    vol_name = get_hashed_name_for_volume("nfs", nfs_inner_config)
    assert output["volumes"] == {vol_name: {"driver_opts": {"type": "nfs", "device": ":/path", "o": "addr=server"}}}
    assert output["services"]["test_container"]["volumes"] == [
        {"type": "volume", "source": vol_name, "target": "/some/path", "read_only": False, "volume": {"nocopy": False}}
    ]


def test_nfs_volume_with_options(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    nfs_inner_config = {"server": "server", "path": "/path", "options": ["vers=3.0", "verbose=true"]}
    nfs_config = {"type": "nfs", "nfs_config": nfs_inner_config}
    c1.add_storage("/some/path", nfs_config)
    output = render.render()
    vol_name = get_hashed_name_for_volume("nfs", nfs_inner_config)
    assert output["volumes"] == {
        vol_name: {
            "driver_opts": {
                "type": "nfs",
                "device": ":/path",
                "o": "addr=server,verbose=true,vers=3.0",
            }
        }
    }
    assert output["services"]["test_container"]["volumes"] == [
        {"type": "volume", "source": vol_name, "target": "/some/path", "read_only": False, "volume": {"nocopy": False}}
    ]


def test_tmpfs_invalid_size(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "tmpfs", "tmpfs_config": {"size": "2"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", vol_config)


def test_tmpfs_zero_size(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "tmpfs", "tmpfs_config": {"size": 0}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", vol_config)


def test_tmpfs_invalid_mode(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "tmpfs", "tmpfs_config": {"mode": "invalid"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", vol_config)


def test_tmpfs_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_storage("/some/path", {"type": "tmpfs"})
    c1.add_storage("/some/other/path", {"type": "tmpfs", "tmpfs_config": {"size": 100}})
    c1.add_storage(
        "/some/other/path2", {"type": "tmpfs", "tmpfs_config": {"size": 100, "mode": "0777", "uid": 1000, "gid": 1000}}
    )
    output = render.render()
    assert output["services"]["test_container"]["tmpfs"] == [
        "/some/other/path2:gid=1000,mode=0777,size=104857600,uid=1000",
        "/some/other/path:size=104857600",
        "/some/path",
    ]


def test_add_tmpfs_with_existing_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_storage("/some/path", {"type": "volume", "volume_config": {"volume_name": "test_volume"}})
    with pytest.raises(Exception):
        c1.add_storage("/some/path", {"type": "tmpfs", "tmpfs_config": {"size": 100}})


def test_add_volume_with_existing_tmpfs(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_storage("/some/path", {"type": "tmpfs", "tmpfs_config": {"size": 100}})
    with pytest.raises(Exception):
        c1.add_storage("/some/path", {"type": "volume", "volume_config": {"volume_name": "test_volume"}})


def test_temporary_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "temporary", "volume_config": {"volume_name": "test_temp_volume"}}
    c1.add_storage("/some/path", vol_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "source": "test_temp_volume",
            "type": "volume",
            "target": "/some/path",
            "read_only": False,
            "volume": {"nocopy": False},
        }
    ]


def test_docker_volume_missing_config(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "volume", "volume_config": {}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", vol_config)


def test_docker_volume_missing_volume_name(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "volume", "volume_config": {"volume_name": ""}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", vol_config)


def test_docker_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "volume", "volume_config": {"volume_name": "test_volume"}}
    c1.add_storage("/some/path", vol_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "volume",
            "source": "test_volume",
            "target": "/some/path",
            "read_only": False,
            "volume": {"nocopy": False},
        }
    ]
    assert output["volumes"] == {"test_volume": {}}


def test_anonymous_volume(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    vol_config = {"type": "anonymous", "volume_config": {"nocopy": True}}
    c1.add_storage("/some/path", vol_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {"type": "volume", "target": "/some/path", "read_only": False, "volume": {"nocopy": True}}
    ]
    assert "volumes" not in output


def test_add_udev(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_udev()
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/run/udev",
            "target": "/run/udev",
            "read_only": True,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_udev_not_read_only(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.add_udev(read_only=False)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/run/udev",
            "target": "/run/udev",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_docker_socket(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.storage._add_docker_socket(mount_path="/var/run/docker.sock")
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/var/run/docker.sock",
            "target": "/var/run/docker.sock",
            "read_only": True,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_docker_socket_not_read_only(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.storage._add_docker_socket(read_only=False, mount_path="/var/run/docker.sock")
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/var/run/docker.sock",
            "target": "/var/run/docker.sock",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_add_docker_socket_mount_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.storage._add_docker_socket(mount_path="/some/path")
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/var/run/docker.sock",
            "target": "/some/path",
            "read_only": True,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]


def test_host_path_with_disallowed_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"path": "/mnt"}}
    with pytest.raises(Exception):
        c1.add_storage("/some/path", host_path_config)


def test_host_path_without_disallowed_path(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    host_path_config = {"type": "host_path", "host_path_config": {"path": "/mnt/test"}}
    c1.add_storage("/mnt", host_path_config)
    output = render.render()
    assert output["services"]["test_container"]["volumes"] == [
        {
            "type": "bind",
            "source": "/mnt/test",
            "target": "/mnt",
            "read_only": False,
            "bind": {"create_host_path": False, "propagation": "rprivate"},
        }
    ]
