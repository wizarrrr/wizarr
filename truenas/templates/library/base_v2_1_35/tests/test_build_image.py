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


def test_build_image_with_from(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.build_image(["FROM test_image"])


def test_build_image_with_from_with_whitespace(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    with pytest.raises(Exception):
        c1.build_image([" FROM test_image"])


def test_build_image(mock_values):
    render = Render(mock_values)
    c1 = render.add_container("test_container", "test_image")
    c1.healthcheck.disable()
    c1.build_image(
        [
            "RUN echo hello",
            None,
            "",
            "RUN echo world",
        ]
    )
    output = render.render()
    assert (
        output["services"]["test_container"]["image"]
        == "ix-nginx:latest_4a127145ea4c25511707e57005dd0ed457fe2f4932082c8f9faa339a450b6a99"
    )
    assert output["services"]["test_container"]["build"] == {
        "tags": ["ix-nginx:latest_4a127145ea4c25511707e57005dd0ed457fe2f4932082c8f9faa339a450b6a99"],
        "dockerfile_inline": """FROM nginx:latest
RUN echo hello
RUN echo world
""",
    }
