from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_dockerfile_sets_default_bind_port_for_runtime_and_healthcheck():
    dockerfile = DOCKERFILE.read_text()

    assert "ENV HOST=0.0.0.0" in dockerfile
    assert "ENV PORT=5690" in dockerfile
    assert "http://localhost:${PORT:-5690}/health" in dockerfile
