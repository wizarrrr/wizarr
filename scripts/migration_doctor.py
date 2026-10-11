#!/usr/bin/env python3
"""
Migration Doctor

CLI helper to diagnose and repair Alembic migration issues for Wizarr.

Typical stuck scenario:
    - User updates Wizarr but their database references an Alembic revision
      that no longer exists in the repository (e.g., after a squashed release).
    - ``flask db upgrade`` fails with "Can't locate revision identified by ..."

This tool inspects the current database state, highlights unknown revisions,
and can stamp the database forward once you confirm the schema is already up
to date. Stamping does **not** run migrations – it only updates the
``alembic_version`` table so normal upgrades can proceed again.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
except ModuleNotFoundError as exc:  # pragma: no cover - defensive guard
    raise SystemExit(
        "Alembic is required to run the migration doctor. "
        "Install dependencies first (e.g., `uv sync` or `pip install -r requirements`)."
    ) from exc
from flask import Flask
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Import Wizarr modules after mutating sys.path
from app.config import DevelopmentConfig, ProductionConfig  # noqa: E402
from app.extensions import db, migrate  # noqa: E402


@dataclass
class RevisionStatus:
    revision: str
    known: bool
    description: str | None
    file_path: Path | None


@dataclass
class StatusReport:
    db_uri: str
    db_path: Path | None
    script_location: Path
    heads: list[RevisionStatus]
    revisions: list[RevisionStatus]
    missing_table: bool
    issues: list[str]


def build_flask_app(database_uri: str | None = None) -> Flask:
    """Create a lightweight Flask app with SQLAlchemy + Flask-Migrate initialized."""
    env = os.getenv("FLASK_ENV", "production").lower()
    config_cls: type[ProductionConfig | DevelopmentConfig]
    config_cls = DevelopmentConfig if env == "development" else ProductionConfig

    app = Flask("wizarr-migration-doctor")
    app.config.from_object(config_cls)
    if database_uri:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

    db.init_app(app)
    migrate.init_app(app, db)
    return app


def build_alembic_config(db_uri: str) -> Config:
    """Create Alembic config tied to the Wizarr migrations directory."""
    migrations_dir = ROOT_DIR / "migrations"
    cfg = Config(str(migrations_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(migrations_dir))
    cfg.set_main_option("sqlalchemy.url", db_uri)
    return cfg


def build_revision_index(script_dir: ScriptDirectory) -> dict[str, object]:
    """Return mapping of revision id -> Script object."""
    return {rev.revision: rev for rev in script_dir.walk_revisions()}


def describe_revision(script_rev) -> tuple[str | None, Path | None]:
    """Extract first-line description and relative path from a Script object."""
    if script_rev is None:
        return None, None

    doc = (script_rev.doc or "").strip()
    if doc:
        doc = doc.splitlines()[0].strip()
    path = Path(script_rev.path)
    try:
        rel_path = path.resolve().relative_to(ROOT_DIR)
    except ValueError:
        rel_path = path.resolve()
    return doc or None, rel_path


def resolve_db_path(uri: str) -> Path | None:
    """Resolve filesystem path for SQLite URLs for nicer display."""
    try:
        url = make_url(uri)
    except Exception:
        return None

    if url.drivername.startswith("sqlite") and url.database:
        return Path(url.database).expanduser()
    return None


def fetch_db_revisions() -> tuple[list[str], bool]:
    """Return (revision_list, missing_table_flag)."""
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as exc:
        if _is_missing_table_error(exc):
            return [], True
        raise

    revisions = [row[0] for row in result]
    return revisions, False


def _is_missing_table_error(exc: SQLAlchemyError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return (
        "no such table" in message
        or "doesn't exist" in message
        or "does not exist" in message
    )


def collect_status(
    db_uri: str, script_dir: ScriptDirectory, revision_index: dict[str, object]
) -> StatusReport:
    """Build status snapshot for printing or automated repair decisions."""
    revisions, missing_table = fetch_db_revisions()
    revision_status: list[RevisionStatus] = []
    issues: list[str] = []

    for rev in revisions:
        script_rev = revision_index.get(rev)
        doc, rel_path = describe_revision(script_rev)
        entry = RevisionStatus(
            revision=rev,
            known=script_rev is not None,
            description=doc,
            file_path=rel_path,
        )
        revision_status.append(entry)

    unknown = [r.revision for r in revision_status if not r.known]
    if unknown:
        joined = ", ".join(unknown)
        issues.append(
            f"Database references unknown revision(s): {joined}. "
            "Stamp to a known revision once you confirm the schema is already up to date."
        )

    if missing_table:
        issues.append(
            "alembic_version table is missing. New databases should be stamped to base/head before upgrading."
        )
    elif not revision_status:
        issues.append("alembic_version table exists but contains no rows.")

    heads = []
    for head in script_dir.get_heads():
        script_rev = revision_index.get(head)
        doc, rel_path = describe_revision(script_rev)
        heads.append(
            RevisionStatus(
                revision=head, known=True, description=doc, file_path=rel_path
            )
        )

    if not missing_table and not unknown and revision_status:
        db_revs = {rev.revision for rev in revision_status}
        repo_heads = set(script_dir.get_heads())
        if db_revs != repo_heads:
            issues.append(
                "Database is behind repository head(s). Run `uv run flask db upgrade` after resolving blockers."
            )

    return StatusReport(
        db_uri=db_uri,
        db_path=resolve_db_path(db_uri),
        script_location=Path(script_dir.dir),
        heads=heads,
        revisions=revision_status,
        missing_table=missing_table,
        issues=issues,
    )


def print_status(report: StatusReport, verbose: bool = False) -> None:
    """Render human-readable report."""
    print("🩺  Wizarr Migration Doctor\n")
    print(f"Database URI: {report.db_uri}")
    if report.db_path:
        print(f"Database Path: {report.db_path}")
    print(f"Migrations Dir: {report.script_location}")
    print()

    print("Repository heads:")
    if report.heads:
        for head in report.heads:
            desc = f" – {head.description}" if head.description else ""
            path = f" ({head.file_path})" if head.file_path else ""
            print(f"  • {head.revision}{desc}{path}")
    else:
        print("  (no migrations found)")
    print()

    print("Database revisions:")
    if report.missing_table:
        print("  ⚠️  alembic_version table not found.")
    elif not report.revisions:
        print("  ⚠️  alembic_version table is empty.")
    else:
        for entry in report.revisions:
            icon = "✔" if entry.known else "✖"
            desc = f" – {entry.description}" if entry.description else ""
            path = f" ({entry.file_path})" if entry.file_path else ""
            suffix = "" if entry.known else "  <-- missing migration script"
            print(f"  {icon} {entry.revision}{path}{desc}{suffix}")
    print()

    if report.issues:
        print("Issues detected:")
        for issue in report.issues:
            print(f"  • {issue}")
    else:
        print("No structural issues detected – database matches known migrations.")

    if verbose:
        print("\nTips:")
        print(
            "  • Run `python scripts/migration_doctor.py repair --assume-up-to-date` to stamp unknown revisions."
        )
        print(
            "  • Run `uv run flask db upgrade` after stamping to apply missing migrations."
        )


def ensure_valid_target(revision: str, revision_index: dict[str, object]) -> None:
    if revision in {"head", "heads", "base"}:
        return
    if revision not in revision_index:
        raise SystemExit(
            f"Revision '{revision}' is not available in migrations/versions."
        )


def confirm(prompt: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def run_stamp(
    cfg: Config, revision: str, revision_index: dict[str, object], auto_yes: bool
) -> None:
    ensure_valid_target(revision, revision_index)
    if not confirm(
        f"About to stamp database to '{revision}'. This does NOT run migrations – continue?",
        auto_yes,
    ):
        print("Aborted.")
        return

    command.stamp(cfg, revision)
    print(
        f"✅ Database stamped to '{revision}'. You can now run `uv run flask db upgrade` if needed."
    )


def run_repair(
    cfg: Config,
    report: StatusReport,
    revision_index: dict[str, object],
    target: str,
    assume_up_to_date: bool,
    auto_yes: bool,
) -> None:
    unknown = [r for r in report.revisions if not r.known]
    needs_table = report.missing_table or not report.revisions

    if not unknown and not needs_table:
        print("No unknown revisions detected – nothing to repair.")
        return

    if not assume_up_to_date:
        print(
            "Refusing to stamp automatically because --assume-up-to-date was not provided.\n"
            "Re-run with --assume-up-to-date once you have verified the schema matches the chosen target."
        )
        return

    ensure_valid_target(target, revision_index)
    reason = (
        "missing alembic_version table" if needs_table else "unknown revision entry"
    )
    if not confirm(
        f"Stamp database ({reason}) to '{target}'? This only updates alembic_version.",
        auto_yes,
    ):
        print("Aborted.")
        return

    command.stamp(cfg, target)
    print(
        f"✅ Database stamped to '{target}'. Follow up with `uv run flask db upgrade` to apply migrations."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnose and repair Alembic migration issues for Wizarr."
    )
    parser.add_argument(
        "--database",
        dest="database_uri",
        help="Override SQLALCHEMY_DATABASE_URI (defaults to config value).",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False
    parser.set_defaults(command="status")

    status = subparsers.add_parser(
        "status", help="Show current migration status (default)."
    )
    status.add_argument(
        "--verbose", action="store_true", help="Print remediation tips."
    )

    stamp = subparsers.add_parser(
        "stamp", help="Force-set database revision without running migrations."
    )
    stamp.add_argument("revision", help="Revision id, 'head', or 'base'.")
    stamp.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt."
    )

    repair = subparsers.add_parser(
        "repair",
        help="Stamp away unknown revisions after confirming schema is up to date.",
    )
    repair.add_argument(
        "--target",
        default="head",
        help="Revision id (or 'head'/'base') to stamp when repairing (default: head).",
    )
    repair.add_argument(
        "--assume-up-to-date",
        action="store_true",
        help="Confirm that the live database schema already matches the target revision.",
    )
    repair.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt."
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    app = build_flask_app(database_uri=args.database_uri)
    cfg = build_alembic_config(app.config["SQLALCHEMY_DATABASE_URI"])
    script_dir = ScriptDirectory.from_config(cfg)
    revision_index = build_revision_index(script_dir)

    with app.app_context():
        report = collect_status(
            app.config["SQLALCHEMY_DATABASE_URI"], script_dir, revision_index
        )

        if args.command == "stamp":
            run_stamp(cfg, args.revision, revision_index, auto_yes=args.yes)
        elif args.command == "repair":
            run_repair(
                cfg,
                report,
                revision_index,
                target=args.target,
                assume_up_to_date=args.assume_up_to_date,
                auto_yes=args.yes,
            )
        else:
            print_status(report, verbose=getattr(args, "verbose", False))


if __name__ == "__main__":
    main()
