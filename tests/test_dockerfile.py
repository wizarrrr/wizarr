import re
from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_dockerfile_sets_default_bind_port_for_runtime_and_healthcheck():
    dockerfile = DOCKERFILE.read_text()

    assert "ENV HOST=0.0.0.0" in dockerfile
    assert "ENV PORT=5690" in dockerfile
    assert "http://localhost:${PORT:-5690}/health" in dockerfile


def test_runtime_image_does_not_ship_node_modules():
    # Join the continuation lines, so that each instruction is on one line.
    instructions = re.sub(r"\\\n\s*", " ", DOCKERFILE.read_text())
    dockerignore = (DOCKERFILE.parent / ".dockerignore").read_text().splitlines()

    # The RUN instruction that builds the assets also removes node_modules ...
    assert re.search(
        r"^RUN .*npm --prefix app/static/? run build\b.*"
        r"&&\s*rm -rf app/static/node_modules\b",
        instructions,
        re.MULTILINE,
    )
    # ... and the build context never contains a local node_modules.
    assert "**/node_modules" in dockerignore
