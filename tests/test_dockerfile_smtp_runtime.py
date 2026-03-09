from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"
RUNTIME_STAGE_MARKER = "# ─── Stage 3: Runtime ─────────────────────────────────────────────────────"


def _runtime_stage() -> str:
    dockerfile = DOCKERFILE.read_text()

    assert RUNTIME_STAGE_MARKER in dockerfile

    return dockerfile.split(RUNTIME_STAGE_MARKER, maxsplit=1)[1]


def test_runtime_stage_installs_nodejs_for_smtp():
    runtime_stage = _runtime_stage()

    assert "RUN apk add --no-cache" in runtime_stage
    assert "nodejs" in runtime_stage


def test_runtime_stage_copies_root_node_modules_for_smtp_notifier():
    assert "COPY --chown=1000:1000 --from=deps /app/node_modules /app/node_modules" in _runtime_stage()
