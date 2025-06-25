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


tests = [
    {
        "name": "add_ports_should_work",
        "inputs": [
            {
                "values": ({"bind_mode": "published", "port_number": 8081}, {"container_port": 8080}),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8082},
                    {"container_port": 8080, "protocol": "udp"},
                ),
                "expect_error": False,
            },
        ],
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress"},
            {"published": 8082, "target": 8080, "protocol": "udp", "mode": "ingress"},
        ],
    },
    {
        "name": "add_duplicate_ports_should_fail",
        "inputs": [
            {
                "values": ({"bind_mode": "published", "port_number": 8081}, {"container_port": 8080}),
                "expect_error": False,
            },
            {
                "values": ({"bind_mode": "published", "port_number": 8081}, {"container_port": 8080}),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_duplicate_port_different_protocol_should_work",
        "inputs": [
            {
                "values": ({"bind_mode": "published", "port_number": 8081}, {"container_port": 8080}),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "protocol": "udp"},
                ),
                "expect_error": False,
            },
        ],
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress"},
            {"published": 8081, "target": 8080, "protocol": "udp", "mode": "ingress"},
        ],
    },
    {
        "name": "adding_same_port_for_both_wildcard_families_should_work",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["0.0.0.0"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["::"]},
                ),
                "expect_error": False,
            },
        ],
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress"},
        ],
    },
    {
        "name": "adding_duplicate_port_for_v4_ip_and_v4_wildcard_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["0.0.0.0"]},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_duplicate_port_for_v4_wildcard_and_v4_ip_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["0.0.0.0"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"]},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_duplicate_port_for_v4_wildcard_and_v6_ip_should_work",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["fd00:1234:5678:abcd::10"]},
                ),
                "expect_error": False,
            },
        ],
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "192.168.1.10"},
            {
                "published": 8081,
                "target": 8080,
                "protocol": "tcp",
                "mode": "ingress",
                "host_ip": "fd00:1234:5678:abcd::10",
            },
        ],
    },
    {
        "name": "adding_duplicate_port_for_v6_wildcard_and_v4_ip_should_work",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["::"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"]},
                ),
                "expect_error": False,
            },
        ],
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "192.168.1.10"},
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "::"},
        ],
    },
    {
        "name": "adding_duplicate_port_for_v6_wildcard_and_v6_ip_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["::"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["fd00:1234:5678:abcd::10"]},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_duplicate_port_for_v6_ip_and_v6_wildcard_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["fd00:1234:5678:abcd::10"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["::"]},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_duplicate_port_with_different_v4_ip_should_work",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.11"]},
                ),
                "expect_error": False,
            },
        ],
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "192.168.1.10"},
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "192.168.1.11"},
        ],
    },
    {
        "name": "adding_port_with_invalid_protocol_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "protocol": "invalid_protocol"},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_port_with_invalid_mode_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "mode": "invalid_mode"},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_port_with_invalid_ip_should_fail",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["invalid_ip"]},
                ),
                "expect_error": True,
            },
        ],
    },
    {
        "name": "adding_port_with_invalid_port_number_should_fail",
        "inputs": [
            {"values": ({"bind_mode": "published", "port_number": -1}, {"container_port": 8080}), "expect_error": True},
        ],
    },
    {
        "name": "adding_port_with_invalid_container_port_should_fail",
        "inputs": [
            {"values": ({"bind_mode": "published", "port_number": 8081}, {"container_port": -1}), "expect_error": True},
        ],
    },
    {
        "name": "adding_duplicate_ports_with_different_host_ip_should_work",
        "inputs": [
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.10"], "protocol": "udp"},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.11"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["192.168.1.11"], "protocol": "udp"},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["fd00:1234:5678:abcd::10"]},
                ),
                "expect_error": False,
            },
            {
                "values": (
                    {"bind_mode": "published", "port_number": 8081},
                    {"container_port": 8080, "host_ips": ["fd00:1234:5678:abcd::11"]},
                ),
                "expect_error": False,
            },
        ],
        # fmt: off
        "expected": [
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "192.168.1.10"},
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "192.168.1.11"},
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "fd00:1234:5678:abcd::10"}, # noqa
            {"published": 8081, "target": 8080, "protocol": "tcp", "mode": "ingress", "host_ip": "fd00:1234:5678:abcd::11"}, # noqa
            {"published": 8081, "target": 8080, "protocol": "udp", "mode": "ingress", "host_ip": "192.168.1.10"},
            {"published": 8081, "target": 8080, "protocol": "udp", "mode": "ingress", "host_ip": "192.168.1.11"},
        ],
        # fmt: on
    },
]


@pytest.mark.parametrize("test", tests)
def test_ports(test):
    mock_values = {
        "images": {
            "test_image": {
                "repository": "nginx",
                "tag": "latest",
            }
        },
    }

    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()

    errored = False
    for input in test["inputs"]:
        if input["expect_error"]:
            with pytest.raises(Exception):
                c1.add_port(*input["values"])
                errored = True
        else:
            c1.add_port(*input["values"])

    errored = True if [i["expect_error"] for i in test["inputs"]].count(True) > 0 else False
    if errored:
        return

    output = render.render()
    assert output["services"]["test_container"]["ports"] == test["expected"]
