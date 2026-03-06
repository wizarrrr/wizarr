"""add smtp fields to notification

Revision ID: 20260306_add_smtp_fields_to_notification
Revises: eecad7c18ac3
Create Date: 2026-03-06 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260306_add_smtp_fields_to_notification"
down_revision = "eecad7c18ac3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.add_column(sa.Column("smtp_port", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("smtp_from_email", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("smtp_to_emails", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("smtp_encryption", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("notification", schema=None) as batch_op:
        batch_op.drop_column("smtp_encryption")
        batch_op.drop_column("smtp_to_emails")
        batch_op.drop_column("smtp_from_email")
        batch_op.drop_column("smtp_port")
