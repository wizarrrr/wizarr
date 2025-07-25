"""Add WebAuthn credentials table

Revision ID: 5805136a1d16
Revises: 20250712_update_wizard_external_url
Create Date: 2025-07-13 17:36:21.350145

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5805136a1d16"
down_revision = "20250712_update_wizard_external_url"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Check if table exists before creating
    inspector = sa.inspect(op.get_bind())
    if "webauthn_credential" not in inspector.get_table_names():
        op.create_table(
            "webauthn_credential",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("admin_account_id", sa.Integer(), nullable=False),
            sa.Column("credential_id", sa.LargeBinary(), nullable=False),
            sa.Column("public_key", sa.LargeBinary(), nullable=False),
            sa.Column("sign_count", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["admin_account_id"],
                ["admin_account.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("credential_id"),
        )
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_invitation_wizard_bundle", "wizard_bundle", ["wizard_bundle_id"], ["id"]
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_constraint("fk_invitation_wizard_bundle", type_="foreignkey")

    op.drop_table("webauthn_credential")
    # ### end Alembic commands ###
