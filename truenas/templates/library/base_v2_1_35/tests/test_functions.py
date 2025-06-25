import re
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


def test_funcs(mock_values):
    mock_values["ix_volumes"] = {"test": "/mnt/test123"}
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()

    tests = [
        {"func": "auto_cast", "values": ["1"], "expected": 1},
        {"func": "auto_cast", "values": ["TrUe"], "expected": True},
        {"func": "auto_cast", "values": ["FaLsE"], "expected": False},
        {"func": "auto_cast", "values": ["0.2"], "expected": 0.2},
        {"func": "auto_cast", "values": [True], "expected": True},
        {"func": "basic_auth_header", "values": ["my_user", "my_pass"], "expected": "Basic bXlfdXNlcjpteV9wYXNz"},
        {"func": "basic_auth", "values": ["my_user", "my_pass"], "expected": "bXlfdXNlcjpteV9wYXNz"},
        {
            "func": "bcrypt_hash",
            "values": ["my_pass"],
            "expect_regex": r"^\$2b\$12\$[a-zA-Z0-9-_\.\/]+$",
        },
        {"func": "camel_case", "values": ["my_user"], "expected": "My_User"},
        {"func": "copy_dict", "values": [{"a": 1}], "expected": {"a": 1}},
        {"func": "fail", "values": ["my_message"], "expect_raise": True},
        {
            "func": "htpasswd",
            "values": ["my_user", "my_pass"],
            "expect_regex": r"^my_user:\$2b\$12\$[a-zA-Z0-9-_\.\/]+$",
        },
        {"func": "is_boolean", "values": ["true"], "expected": True},
        {"func": "is_boolean", "values": ["false"], "expected": True},
        {"func": "is_number", "values": ["1"], "expected": True},
        {"func": "is_number", "values": ["1.1"], "expected": True},
        {"func": "match_regex", "values": ["value", "^[a-zA-Z0-9]+$"], "expected": True},
        {"func": "match_regex", "values": ["value", "^[0-9]+$"], "expected": False},
        {"func": "merge_dicts", "values": [{"a": 1}, {"b": 2}], "expected": {"a": 1, "b": 2}},
        {"func": "must_match_regex", "values": ["my_user", "^[0-9]$"], "expect_raise": True},
        {"func": "must_match_regex", "values": ["1", "^[0-9]$"], "expected": "1"},
        {"func": "secure_string", "values": [10], "expect_regex": r"^[a-zA-Z0-9-_]+$"},
        {"func": "disallow_chars", "values": ["my_user", ["$", "@"], "my_key"], "expected": "my_user"},
        {"func": "disallow_chars", "values": ["my_user$", ["$", "@"], "my_key"], "expect_raise": True},
        {
            "func": "get_host_path",
            "values": [{"type": "host_path", "host_path_config": {"path": "/mnt/test"}}],
            "expected": "/mnt/test",
        },
        {
            "func": "get_host_path",
            "values": [{"type": "ix_volume", "ix_volume_config": {"dataset_name": "test"}}],
            "expected": "/mnt/test123",
        },
        {"func": "or_default", "values": [None, 1], "expected": 1},
        {"func": "or_default", "values": [1, None], "expected": 1},
        {"func": "or_default", "values": [False, 1], "expected": 1},
        {"func": "or_default", "values": [True, 1], "expected": True},
        {"func": "temp_config", "values": [""], "expect_raise": True},
        {
            "func": "temp_config",
            "values": ["test"],
            "expected": {"type": "temporary", "volume_config": {"volume_name": "test"}},
        },
        {"func": "require_unique", "values": [["a=1", "b=2", "c"], "values.key", "="], "expected": None},
        {
            "func": "require_unique",
            "values": [["a=1", "b=2", "b=3"], "values.key", "="],
            "expect_raise": True,
        },
        {
            "func": "require_no_reserved",
            "values": [["a=1", "b=2", "c"], "values.key", ["d"], "="],
            "expected": None,
        },
        {
            "func": "require_no_reserved",
            "values": [["a=1", "b=2", "c"], "values.key", ["a"], "="],
            "expect_raise": True,
        },
        {
            "func": "require_no_reserved",
            "values": [["a=1", "b=2", "c"], "values.key", ["b"], "=", True],
            "expect_raise": True,
        },
        {
            "func": "url_encode",
            "values": ["7V!@@%%63r@a5#e!2X9!68g4b"],
            "expected": "7V%21%40%40%25%2563r%40a5%23e%212X9%2168g4b",
        },
    ]

    for test in tests:
        print(test["func"], test)
        func = render.funcs[test["func"]]
        if test.get("expect_raise", False):
            with pytest.raises(Exception):
                func(*test["values"])
        elif test.get("expect_regex"):
            r = func(*test["values"])
            assert re.match(test["expect_regex"], r) is not None
        else:
            r = func(*test["values"])
            assert r == test["expected"]
