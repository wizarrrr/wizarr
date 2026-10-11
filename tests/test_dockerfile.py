from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_dockerfile_sets_default_bind_port_for_runtime_and_healthcheck():
    dockerfile = DOCKERFILE.read_text()

    assert "ENV HOST=0.0.0.0" in dockerfile
    assert "ENV PORT=5690" in dockerfile
    assert "http://localhost:${PORT:-5690}/health" in dockerfile


def test_runtime_image_does_not_ship_node_modules():
    dockerfile = DOCKERFILE.read_text()
    dockerignore = (DOCKERFILE.parent / ".dockerignore").read_text().splitlines()

    # The builder removes node_modules after the asset build ...
    assert (
        "npm --prefix app/static/ run build \\\n    && rm -rf app/static/node_modules"
        in dockerfile
    )
    # ... and the build context never contains a local node_modules.
    assert "**/node_modules" in dockerignore
