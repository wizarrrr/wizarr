"""Repair invitation_user data lost by LDAP migration CASCADE bug

The 20251226_add_ldap migration ran batch_alter_table("invitation") with
PRAGMA foreign_keys=ON.  In SQLite, DROP TABLE with FKs enabled triggers
an implicit DELETE FROM which fires ON DELETE CASCADE — wiping every row
in invitation_user.  This migration repopulates the table using the same
recovery logic from the original 20250814 migration.

Revision ID: 20260401_repair
Revises: 8e5c69f96870
Create Date: 2026-04-01 23:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260401_repair"
down_revision = "8e5c69f96870"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Check if invitation_user table exists (it should)
    inspector = sa.inspect(conn)
    if "invitation_user" not in inspector.get_table_names():
        print("WARNING: invitation_user table does not exist, skipping repair")
        return

    # Check current state — skip if data is already present
    existing = conn.execute(sa.text("SELECT COUNT(*) FROM invitation_user")).scalar()
    if existing > 0:
        print(
            f"invitation_user already has {existing} rows — skipping repair "
            f"(data was not affected by the CASCADE bug)"
        )
        return

    print("invitation_user is empty — running data recovery...")

    # Step 1: Recover from invitation.used_by_id → user relationship
    result1 = conn.execute(
        sa.text("""
        SELECT i.id as invite_id, i.used_by_id as user_id,
               COALESCE(i.used_at, i.created) as used_at,
               u.server_id as server_id
        FROM invitation i
        JOIN user u ON i.used_by_id = u.id
        WHERE i.used_by_id IS NOT NULL
    """)
    )

    step1_count = 0
    for row in result1:
        conn.execute(
            sa.text("""
            INSERT OR IGNORE INTO invitation_user (invite_id, user_id, used_at, server_id)
            VALUES (:invite_id, :user_id, :used_at, :server_id)
        """),
            {
                "invite_id": row.invite_id,
                "user_id": row.user_id,
                "used_at": row.used_at,
                "server_id": row.server_id,
            },
        )
        step1_count += 1

    if step1_count:
        print(f"  Step 1: Recovered {step1_count} rows from invitation.used_by_id")

    # Step 2: Recover from user.code ↔ invitation.code matching
    # This captures users from unlimited invitations (multiple users per code)
    result2 = conn.execute(
        sa.text("""
        SELECT DISTINCT i.id as invite_id, u.id as user_id,
               COALESCE(i.used_at, i.created) as used_at,
               u.server_id as server_id
        FROM invitation i
        JOIN user u ON u.code = i.code
        WHERE u.code IS NOT NULL
          AND u.code != ''
          AND NOT EXISTS (
              SELECT 1 FROM invitation_user iu
              WHERE iu.invite_id = i.id AND iu.user_id = u.id
          )
    """)
    )

    step2_count = 0
    for row in result2:
        conn.execute(
            sa.text("""
            INSERT OR IGNORE INTO invitation_user (invite_id, user_id, used_at, server_id)
            VALUES (:invite_id, :user_id, :used_at, :server_id)
        """),
            {
                "invite_id": row.invite_id,
                "user_id": row.user_id,
                "used_at": row.used_at,
                "server_id": row.server_id,
            },
        )
        step2_count += 1

    if step2_count:
        print(
            f"  Step 2: Recovered {step2_count} additional rows from user.code matching"
        )

    # Step 3: Fix invitation_server usage flags for consistency
    invitations_with_users = conn.execute(
        sa.text("SELECT DISTINCT invite_id FROM invitation_user")
    ).fetchall()

    server_fixes = 0
    for row in invitations_with_users:
        invite_id = row.invite_id

        result = conn.execute(
            sa.text("""
            UPDATE invitation_server
            SET used = 1, used_at = CURRENT_TIMESTAMP
            WHERE invite_id = :invite_id AND used = 0
        """),
            {"invite_id": invite_id},
        )
        if result.rowcount > 0:
            server_fixes += result.rowcount

        conn.execute(
            sa.text("""
            UPDATE invitation
            SET used = 1, used_at = COALESCE(used_at, CURRENT_TIMESTAMP)
            WHERE id = :invite_id AND used = 0
        """),
            {"invite_id": invite_id},
        )

    total = step1_count + step2_count
    print(f"  Recovery complete: {total} invitation-user relationships restored")
    if server_fixes:
        print(f"  Fixed {server_fixes} invitation_server usage flags")


def downgrade():
    # This is a data-repair migration — downgrade is a no-op.
    # The repopulated data is correct and should not be removed.
    pass
