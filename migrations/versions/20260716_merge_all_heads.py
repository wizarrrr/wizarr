"""Merge all migration heads into single linear history

This migration resolves "Multiple head revisions are present" error by merging
the two separate migration branches:
- Branch 1: 20251226_add_ldap → 8e5c69f96870
- Branch 2: 080eaac6e013, c854ad44aad5 → eecad7c18ac3

After this merge, the migration history becomes linear and deployment errors are resolved.

Revision ID: 20260716_merge_all_heads
Revises: 8e5c69f96870, eecad7c18ac3
Create Date: 2026-07-16 12:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "20260716_merge_all_heads"
down_revision = ("8e5c69f96870", "eecad7c18ac3")
branch_labels = None
depends_on = None


def upgrade():
    """No schema changes - this is purely a structural merge of migration branches."""
    pass


def downgrade():
    """No schema changes to reverse."""
    pass
