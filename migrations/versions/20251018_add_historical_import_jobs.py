"""add historical import jobs table

Revision ID: 20251018_add_hist_jobs
Revises: 5c6fa54db3b1
Create Date: 2025-10-18 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251018_add_hist_jobs"
down_revision = "5c6fa54db3b1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "historical_import_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("days_back", sa.Integer(), nullable=False),
        sa.Column("max_results", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="queued"
        ),
        sa.Column("total_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["media_server.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_historical_import_job_server_id",
        "historical_import_job",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        "ix_historical_import_job_status",
        "historical_import_job",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_historical_import_job_server_status",
        "historical_import_job",
        ["server_id", "status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_historical_import_job_server_status",
        table_name="historical_import_job",
    )
    op.drop_index("ix_historical_import_job_status", table_name="historical_import_job")
    op.drop_index(
        "ix_historical_import_job_server_id",
        table_name="historical_import_job",
    )
    op.drop_table("historical_import_job")
