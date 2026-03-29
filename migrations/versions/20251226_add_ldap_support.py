"""add LDAP authentication and user management support

Revision ID: 20251226_add_ldap
Revises: eecad7c18ac3
Create Date: 2025-12-26 17:39:49.893162

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251226_add_ldap"
down_revision = "e6155a91eb50"
branch_labels = None
depends_on = None


def _has_column(inspector, table, column):
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # ── New tables ────────────────────────────────────────────────────────
    # Guarded with IF NOT EXISTS checks because a prior failed run may have
    # created these tables before crashing (SQLite has no transactional DDL,
    # so partial DDL changes persist even when the migration fails).
    if "ldap_configuration" not in existing_tables:
        op.create_table(
            "ldap_configuration",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("server_url", sa.String(), nullable=False),
            sa.Column("use_tls", sa.Boolean(), nullable=False),
            sa.Column("verify_cert", sa.Boolean(), nullable=False),
            sa.Column("service_account_dn", sa.String(), nullable=True),
            sa.Column("service_account_password_encrypted", sa.String(), nullable=True),
            sa.Column("user_base_dn", sa.String(), nullable=False),
            sa.Column("user_search_filter", sa.String(), nullable=False),
            sa.Column("user_object_class", sa.String(), nullable=False),
            sa.Column("username_attribute", sa.String(), nullable=False),
            sa.Column("email_attribute", sa.String(), nullable=False),
            sa.Column("group_base_dn", sa.String(), nullable=True),
            sa.Column("group_object_class", sa.String(), nullable=False),
            sa.Column("group_member_attribute", sa.String(), nullable=False),
            sa.Column("admin_group_dn", sa.String(), nullable=True),
            sa.Column("allow_admin_bind", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "ldap_group" not in existing_tables:
        op.create_table(
            "ldap_group",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dn", sa.String(), nullable=False),
            sa.Column("cn", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dn"),
        )

    # ── Alter admin_account ───────────────────────────────────────────────
    # SQLite batch_alter_table recreates the table via DROP + CREATE.
    # webauthn_credential and api_key have FKs pointing at admin_account,
    # so the DROP fails when PRAGMA foreign_keys=ON.  Temporarily disable
    # FK enforcement for this operation.
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("admin_account", schema=None) as batch_op:
            if not _has_column(inspector, "admin_account", "auth_source"):
                batch_op.add_column(
                    sa.Column(
                        "auth_source",
                        sa.String(),
                        nullable=False,
                        server_default="local",
                    )
                )
            if not _has_column(inspector, "admin_account", "external_id"):
                batch_op.add_column(
                    sa.Column("external_id", sa.String(), nullable=True)
                )
            batch_op.alter_column(
                "password_hash", existing_type=sa.String(), nullable=True
            )
    finally:
        conn.execute(sa.text("PRAGMA foreign_keys=ON"))

    # ── Alter invitation ──────────────────────────────────────────────────
    if not _has_column(inspector, "invitation", "create_ldap_user"):
        with op.batch_alter_table("invitation", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "create_ldap_user",
                    sa.Boolean(),
                    nullable=False,
                    server_default="0",
                )
            )

    # ── Alter user ────────────────────────────────────────────────────────
    if not _has_column(inspector, "user", "is_ldap_user"):
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_ldap_user", sa.Boolean(), nullable=False, server_default="0"
                )
            )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("is_ldap_user")

    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_column("create_ldap_user")

    conn = op.get_bind()
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("admin_account", schema=None) as batch_op:
            batch_op.alter_column(
                "password_hash", existing_type=sa.String(), nullable=False
            )
            batch_op.drop_column("external_id")
            batch_op.drop_column("auth_source")
    finally:
        conn.execute(sa.text("PRAGMA foreign_keys=ON"))

    op.drop_table("ldap_group")
    op.drop_table("ldap_configuration")
