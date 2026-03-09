from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_runtime_stage_installs_nodejs_for_smtp():
    dockerfile = DOCKERFILE.read_text()

    runtime_stage = dockerfile.split("FROM ghcr.io/astral-sh/uv:python3.13-alpine", maxsplit=2)[
        2
    ]

    assert "RUN apk add --no-cache curl tzdata su-exec nodejs" in runtime_stage


def test_runtime_stage_copies_root_node_modules_for_smtp_notifier():
    dockerfile = DOCKERFILE.read_text()

    assert "COPY --chown=1000:1000 --from=deps /app/node_modules /app/node_modules" in (
        dockerfile
    )
