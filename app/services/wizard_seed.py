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
# bundled markdown files are only used to:
# 1. Bootstrap fresh installations with all default steps
# 2. Add steps for NEW server types on upgrades (not new steps for existing types)


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
    """Ensure the database contains wizard steps for server types.

    Behavior:
    • First installation (empty wizard_step table): Import all default steps
    • Upgrades: Only import steps for NEW server types that don't exist in DB yet
    • Existing steps are never modified to preserve UI customizations
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
    # 2. Check if this is a fresh installation or upgrade
    # ------------------------------------------------------------------
    existing_server_types = set(
        db.session.query(WizardStep.server_type).distinct().all()
    )
    existing_server_types = {row[0] for row in existing_server_types}

    is_fresh_install = len(existing_server_types) == 0

    # ------------------------------------------------------------------
    # 3. Determine which server types to process
    # ------------------------------------------------------------------
    if is_fresh_install:
        # Fresh install: import all server types
        server_types_to_import = set(builtin_sources.keys())
        current_app.logger.info(
            f"Fresh install detected: importing wizard steps for all {len(server_types_to_import)} server types"
        )
    else:
        # Upgrade: only import NEW server types not in database
        available_server_types = set(builtin_sources.keys())
        server_types_to_import = available_server_types - existing_server_types

        if server_types_to_import:
            current_app.logger.info(
                f"Upgrade detected: importing wizard steps for {len(server_types_to_import)} new server types: {sorted(server_types_to_import)}"
            )
        else:
            current_app.logger.debug("Upgrade detected: no new server types to import")

    # ------------------------------------------------------------------
    # 4. Import steps for determined server types only
    # ------------------------------------------------------------------
    for server_type in server_types_to_import:
        files = builtin_sources[server_type]
        files_sorted = sorted(files)

        for pos, path in enumerate(files_sorted):
            # Create new row for this step
            meta = _parse_markdown(path)
            step = WizardStep(
                server_type=server_type,
                position=pos,
                title=meta["title"],
                markdown=meta["markdown"],
                requires=meta["requires"],
            )
            db.session.add(step)

    if server_types_to_import:
        db.session.commit()
        current_app.logger.info(
            f"Successfully imported wizard steps for: {sorted(server_types_to_import)}"
        )

    # NOTE: existing steps are never modified to preserve UI customizations.
    # This function only imports steps for server types that don't exist yet.
