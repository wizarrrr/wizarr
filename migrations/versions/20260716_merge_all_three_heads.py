"""Merge all three migration heads into single linear history

This resolves "Multiple head revisions are present" by merging:
- 8e5c69f96870 (LDAP merge)
- eecad7c18ac3 (Max sessions merge)
- 20260506_pakasir_qris (QRIS tables)

Revision ID: 20260716_final_merge_all_heads
Revises: 8e5c69f96870, eecad7c18ac3, 20260506_pakasir_qris
Create Date: 2026-07-16 16:30:00.000000
"""

revision = "20260716_final_merge_all_heads"
down_revision = ("8e5c69f96870", "eecad7c18ac3", "20260506_pakasir_qris")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
