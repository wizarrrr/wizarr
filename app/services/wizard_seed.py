from __future__ import annotations

from pathlib import Path
from typing import List

import frontmatter
from flask import current_app

from app.extensions import db
from app.models import WizardStep

# Folder containing the bundled markdown files (wizard_steps/<server>/*.md)
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "wizard_steps"

# Directory where *custom* wizard step markdown may exist (former bind-mount)
CUSTOM_DIR = Path("/data/wizard_steps")


def _gather_step_files() -> List[Path]:
    """Return all bundled markdown files."""
    if not BASE_DIR.exists():
        return []
    return list(BASE_DIR.rglob("*.md"))


def _collect_server_files(root: Path) -> dict[str, list[Path]]:
    """Return mapping *server_type* → list[Path] under *root* (markdown only).

    Ignores the *root* directory completely if it does not exist.  Files are
    collected recursively so both flat and nested structures work.
    """
    if not root.exists():
        return {}

    server_dirs: dict[str, list[Path]] = {}
    for path in root.rglob("*.md"):
        server = path.parent.name  # assumes layout: <root>/<server_type>/<file>.md
        server_dirs.setdefault(server, []).append(path)
    return server_dirs


def _parse_markdown(path: Path) -> dict:
    post = frontmatter.load(path)
    requires = post.get("requires", [])  # list[str]
    title = post.get("title")

    # If no explicit title in front-matter, derive from first markdown header
    if not title:
        for line in post.content.splitlines():
            if line.lstrip().startswith("# "):
                title = line.lstrip("# ").strip()
                break

    return {
        "title": title,
        "markdown": post.content,
        "requires": requires,
    }


def import_default_wizard_steps() -> None:
    """Seed the DB with wizard steps bundled as markdown files.

    • For every *server_type* directory create rows ordered lexicographically by
      filename.  Import only if **no** WizardStep rows for that server exist –
      so local edits survive restarts/upgrades.
    """

    # Skip entirely when running under pytest / testing
    if current_app.config.get("TESTING"):
        return

    # ------------------------------------------------------------------
    # 1. Prepare source pools – custom dir has precedence over built-in ones
    # ------------------------------------------------------------------
    custom_sources  = _collect_server_files(CUSTOM_DIR)
    builtin_sources = _collect_server_files(BASE_DIR)

    # Merge keys so we cover servers that exist only in one of the pools.
    all_servers: set[str] = set(custom_sources) | set(builtin_sources)

    for server_type in sorted(all_servers):
        # Skip import for servers that already have at least one step row
        exists = (
            db.session.query(WizardStep.id)
            .filter_by(server_type=server_type)
            .limit(1)
            .scalar()
        )
        if exists:
            continue

        # Prefer custom markdown if present; otherwise use built-in defaults
        files = custom_sources.get(server_type) or builtin_sources.get(server_type) or []

        # Sort files for stable ordering
        for pos, path in enumerate(sorted(files)):
            meta = _parse_markdown(path)
            step = WizardStep(
                server_type=server_type,
                position=pos,
                title=meta["title"],
                markdown=meta["markdown"],
                requires=meta["requires"],
            )
            db.session.add(step)

    db.session.commit() 