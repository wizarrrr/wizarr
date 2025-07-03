"""add wizard_bundle tables and link to invitation

Revision ID: 20250703_add_wizard_bundle_tables
Revises: 20250702_add_jellyfin_options
Create Date: 2025-07-03 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20250703_add_wizard_bundle_tables"
down_revision = "20250702_add_jellyfin_options"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    # ── 1) wizard_bundle ───────────────────────────────────────────
    if not insp.has_table("wizard_bundle"):
        op.create_table(
            "wizard_bundle",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
        )

    # ── 2) wizard_bundle_step ──────────────────────────────────────
    if not insp.has_table("wizard_bundle_step"):
        op.create_table(
            "wizard_bundle_step",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("bundle_id", sa.Integer, sa.ForeignKey("wizard_bundle.id", ondelete="CASCADE"), nullable=False),
            sa.Column("step_id", sa.Integer, sa.ForeignKey("wizard_step.id", ondelete="CASCADE"), nullable=False),
            sa.Column("position", sa.Integer, nullable=False),
        )
        op.create_unique_constraint(
            "uq_bundle_pos", "wizard_bundle_step", ["bundle_id", "position"]
        )

    cols = {c['name'] for c in insp.get_columns('invitation')}
    # ── 3) invitation.wizard_bundle_id ─────────────────────────────
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        if 'wizard_bundle_id' not in cols:
            batch_op.add_column(sa.Column("wizard_bundle_id", sa.Integer, nullable=True))
            batch_op.create_foreign_key(
                "fk_invitation_bundle", "wizard_bundle", ["wizard_bundle_id"], ["id"]
            )


def downgrade():
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_constraint("fk_invitation_bundle", type_="foreignkey")
        batch_op.drop_column("wizard_bundle_id")

    op.drop_constraint("uq_bundle_pos", "wizard_bundle_step", type_="unique")
    op.drop_table("wizard_bundle_step")
    op.drop_table("wizard_bundle") 