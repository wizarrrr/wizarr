#!/usr/bin/env python3
# scripts/migrate_libraries.py

import os
import click
from flask import Flask
from app import create_app, db
from app.models import Settings, Library, Invitation

@click.command()
def migrate_libraries():
    """Migrate old comma-strings into the new Library + invite_library tables."""
    app = create_app()
    with app.app_context():
        # 1) load and split the global Settings.libraries
        row = Settings.query.filter_by(key="libraries").first()
        old_global = []
        if row and row.value:
            old_global = [s.strip() for s in row.value.split(",") if s.strip()]

        # 2) upsert each as a Library record, enabled=True
        for ext in old_global:
            lib = Library.query.filter_by(external_id=ext).first()
            if not lib:
                lib = Library(external_id=ext, name=ext, enabled=True)
                db.session.add(lib)

        # clear out the old global setting
        if row:
            row.value = ""
        db.session.commit()
        click.echo(f"Imported {len(old_global)} global libraries → Library table.")

        # 3) for each existing invitation, migrate its specific_libraries
        invites = Invitation.query.all()
        count = 0
        for inv in invites:
            if inv.specific_libraries:
                choices = [s.strip() for s in inv.specific_libraries.split(",") if s.strip()]
                for ext in choices:
                    lib = Library.query.filter_by(external_id=ext).first()
                    if lib and lib not in inv.libraries:
                        inv.libraries.append(lib)
                        count += 1
                # clear out the old string
                inv.specific_libraries = None
        db.session.commit()
        click.echo(f"Wired up {count} invite↔library links.")

        # 4) (optional) drop the old specific_libraries column
        #     You can do that via Alembic in a separate revision, or here:
        #     db.engine.execute("ALTER TABLE invitation DROP COLUMN specific_libraries")

        click.echo("✅ Migration complete.")

if __name__ == "__main__":
    migrate_libraries()
