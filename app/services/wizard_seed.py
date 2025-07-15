from __future__ import annotations

from pathlib import Path

import frontmatter
from flask import current_app
from sqlalchemy import inspect  # NEW

from app.extensions import db
from app.models import WizardStep

# Folder containing the bundled markdown files (wizard_steps/<server>/*.md)
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "wizard_steps"

# No override directory – wizard steps are now managed from the UI.  The
# bundled markdown files are only used to bootstrap **new** installations or
# to append *new* default steps introduced in later upgrades.


def _gather_step_files() -> list[Path]:
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
    post = frontmatter.load(str(path))
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


def _collect_builtin_files() -> dict[str, list[Path]]:
    """Return mapping *server_type* → list[Path] for built-in markdown files."""
    return _collect_server_files(BASE_DIR)


def import_default_wizard_steps() -> None:
    """Ensure the database contains at least the bundled *default* wizard
    steps shipped with Wizarr.

    • For every *server_type* directory import the markdown files in
      lexicographical order.
    • Rows that already exist (same *server_type*, *position*) are left
      untouched so UI edits persist.
    • Missing rows are appended – this covers both fresh installations (zero
      rows) and software upgrades that introduce *new* default pages.
    """

    # Skip entirely when running under pytest / testing
    if current_app.config.get("TESTING"):
        return

    # ─── Guard: table might not exist (first run before migrations) ─────────
    # Avoid querying WizardStep if its table is absent to prevent errors when
    # the app factory is invoked by commands that run *before* Alembic
    # migrations (e.g. `flask db upgrade`).  In that scenario the bootstrap
    # should be a no-op and will run again once the app starts for real.
    inspector = inspect(db.engine)
    if not inspector.has_table(WizardStep.__tablename__):
        return

    # ------------------------------------------------------------------
    # 1. Gather built-in wizard step markdown files
    # ------------------------------------------------------------------
    builtin_sources = _collect_builtin_files()

    # Nothing to do if repository contains no markdown assets
    if not builtin_sources:
        return

    # ------------------------------------------------------------------
    # 2. For each server_type ensure *all* default steps exist – we insert
    #    rows *individually* so existing user edits remain intact.
    # ------------------------------------------------------------------
    for server_type, files in builtin_sources.items():
        # Sort files for deterministic position assignment
        files_sorted = sorted(files)

        for pos, path in enumerate(files_sorted):
            # Skip if a row already exists for this (server_type, position)
            exists = (
                db.session.query(WizardStep.id)
                .filter_by(server_type=server_type, position=pos)
                .limit(1)
                .scalar()
            )
            if exists:
                continue

            # Create new row for missing step
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

    # NOTE: existing steps that the admin has modified via the UI are left
    # untouched.  Likewise we do not attempt to remove steps that no longer
    # exist upstream – they might hold valuable custom edits made by the
    # admin.  This function therefore acts as an *append-only* bootstrap.
