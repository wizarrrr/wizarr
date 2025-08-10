"""add admin account table

Revision ID: 20250705_add_admin_account_table
Revises: 20250703_add_wizard_bundle_tables
Create Date: 2025-07-05 00:00:00.000000

"""

import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250705_add_admin_account_table"
down_revision = "e6006b5e374e"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1) Create new table ─────────────────────────────────────────────────
    op.create_table(
        "admin_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=lambda: datetime.datetime.now(datetime.UTC),
        ),
    )

    # ── 2) Migrate legacy single-admin credentials ─────────────────────────
    conn = op.get_bind()
    username = conn.execute(
        sa.text("SELECT value FROM settings WHERE key='admin_username'")
    ).scalar()
    password_hash = conn.execute(
        sa.text("SELECT value FROM settings WHERE key='admin_password'")
    ).scalar()

    if username and password_hash:
        conn.execute(
            sa.text(
                "INSERT INTO admin_account (username, password_hash, created_at) "
                "VALUES (:u, :p, :c)"
            ),
            {
                "u": username,
                "p": password_hash,
                "c": datetime.datetime.now(datetime.UTC),
            },
        )


def downgrade():
    op.drop_table("admin_account")
