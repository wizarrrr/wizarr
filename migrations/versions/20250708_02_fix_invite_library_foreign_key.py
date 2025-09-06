"""fix invite_library foreign key constraint

Revision ID: 91865b5a23d2
Revises: 20250703_add_wizard_bundle_tables
Create Date: 2025-07-08 18:23:51.863438

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "91865b5a23d2"
down_revision = "20250703_add_wizard_bundle_tables"
branch_labels = None
depends_on = None


def upgrade():
    """Fix invite_library foreign key constraint to point to library instead of library_old."""

    conn = op.get_bind()

    # Only handle SQLite - other databases would need different approach
    if conn.dialect.name == "sqlite":
        # Disable foreign key checks
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

        # 1) Rename existing invite_library table
        op.execute("ALTER TABLE invite_library RENAME TO invite_library_old")

        # 2) Create new invite_library table with correct foreign key
        op.create_table(
            "invite_library",
            sa.Column("invite_id", sa.Integer, nullable=False),
            sa.Column("library_id", sa.Integer, nullable=False),
            sa.PrimaryKeyConstraint("invite_id", "library_id"),
            sa.ForeignKeyConstraint(["invite_id"], ["invitation.id"]),
            sa.ForeignKeyConstraint(
                ["library_id"], ["library.id"]
            ),  # Fixed: now points to library, not library_old
        )

        # 3) Copy data from old table to new table
        op.execute(
            "INSERT INTO invite_library (invite_id, library_id) "
            "SELECT invite_id, library_id FROM invite_library_old"
        )

        # 4) Drop the old table
        op.execute("DROP TABLE invite_library_old")

        # Re-enable foreign key checks
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    else:
        # For other databases, we would need to drop and recreate the foreign key constraint
        # This is a simplified approach - in practice you'd want to handle this properly
        with op.batch_alter_table("invite_library", schema=None) as batch_op:
            batch_op.drop_constraint(
                "invite_library_library_id_fkey", type_="foreignkey"
            )
            batch_op.create_foreign_key(
                "invite_library_library_id_fkey", "library", ["library_id"], ["id"]
            )


def downgrade():
    """Revert the foreign key constraint fix (not recommended - this would break the schema)."""

    conn = op.get_bind()

    # Note: This downgrade is problematic because it would point back to library_old
    # which doesn't exist. In practice, you probably don't want to downgrade this.
    if conn.dialect.name == "sqlite":
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

        op.execute("ALTER TABLE invite_library RENAME TO invite_library_new")

        op.create_table(
            "invite_library",
            sa.Column("invite_id", sa.Integer, nullable=False),
            sa.Column("library_id", sa.Integer, nullable=False),
            sa.PrimaryKeyConstraint("invite_id", "library_id"),
            sa.ForeignKeyConstraint(["invite_id"], ["invitation.id"]),
            sa.ForeignKeyConstraint(
                ["library_id"], ["library_old.id"]
            ),  # This would break if library_old doesn't exist
        )

        op.execute(
            "INSERT INTO invite_library (invite_id, library_id) "
            "SELECT invite_id, library_id FROM invite_library_new"
        )

        op.execute("DROP TABLE invite_library_new")

        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
