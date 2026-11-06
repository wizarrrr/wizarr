"""add OIDC admin-panel SSO support

Revision ID: 20260922_add_oidc
Revises: 20260901_expired_unique
Create Date: 2026-09-22 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260922_add_oidc"
down_revision = "20260901_expired_unique"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Guarded with an existence check because SQLite has no transactional
    # DDL -- a prior failed run may have already created this table.
    if "oidc_configuration" not in existing_tables:
        op.create_table(
            "oidc_configuration",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("display_name", sa.String(), nullable=False),
            sa.Column("discovery_url", sa.String(), nullable=False),
            sa.Column("client_id", sa.String(), nullable=False),
            sa.Column("client_secret_encrypted", sa.String(), nullable=True),
            sa.Column("scopes", sa.String(), nullable=False),
            sa.Column("username_claim", sa.String(), nullable=False),
            sa.Column("admin_claim", sa.String(), nullable=True),
            sa.Column("admin_claim_values", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade():
    op.drop_table("oidc_configuration")
