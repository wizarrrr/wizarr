from __future__ import annotations

from pathlib import Path
from typing import List

import frontmatter
from flask import current_app

from app.extensions import db
from app.models import WizardStep

# Folder containing the bundled markdown files (wizard_steps/<server>/*.md)
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "wizard_steps"


def _gather_step_files() -> List[Path]:
    """Return all bundled markdown files."""
    if not BASE_DIR.exists():
        return []
    return list(BASE_DIR.rglob("*.md"))


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

    paths = _gather_step_files()
    if not paths:
        return

    # Group by server folder name
    server_dirs: dict[str, list[Path]] = {}
    for p in paths:
        server = p.parent.name  # e.g. "plex"
        server_dirs.setdefault(server, []).append(p)

    for server_type, files in server_dirs.items():
        # Skip if there are any existing steps for this server
        exists = (
            db.session.query(WizardStep.id)
            .filter_by(server_type=server_type)
            .limit(1)
            .scalar()
        )
        if exists:
            continue

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