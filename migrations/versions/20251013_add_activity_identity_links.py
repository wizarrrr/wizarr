"""add identity links to activity sessions

Revision ID: 4e1d547c2f7a
Revises: 20250921_plus_features
Create Date: 2025-10-13 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4e1d547c2f7a"
down_revision = "20250921_plus_features"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("activity_session", schema=None) as batch_op:
        batch_op.add_column(sa.Column("wizarr_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("wizarr_identity_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_activity_session_wizarr_user_id", ["wizarr_user_id"], unique=False
        )
        batch_op.create_index(
            "ix_activity_session_wizarr_identity_id",
            ["wizarr_identity_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_activity_session_wizarr_user",
            "user",
            ["wizarr_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_activity_session_wizarr_identity",
            "identity",
            ["wizarr_identity_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("activity_session", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_activity_session_wizarr_identity", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_activity_session_wizarr_user", type_="foreignkey")
        batch_op.drop_index("ix_activity_session_wizarr_identity_id")
        batch_op.drop_index("ix_activity_session_wizarr_user_id")
        batch_op.drop_column("wizarr_identity_id")
        batch_op.drop_column("wizarr_user_id")
