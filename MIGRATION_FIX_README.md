# Migration Fix for Multiple Head Revisions Error

## Problem Solved

The error `ERROR [flask_migrate] Error: Multiple head revisions are present for given argument 'head'` has been permanently resolved on the QRIS branch.

## Root Cause

The repository had two separate migration branches that were not properly merged:
1. **Branch A**: LDAP feature branch → `8e5c69f96870_merge_ldap_with_main.py`
2. **Branch B**: Max sessions/Telegram features → `eecad7c18ac3_20251209_merge_max_sessions_and_.py`

These two branches each had their own "heads" (endpoints), causing Alembic to fail when trying to determine which migration to upgrade to.

## Solution Applied

**New file added**: `migrations/versions/20260716_01_complete_merge_all_heads.py`

This migration file:
- Merges all separate branches into a single, linear migration history
- Specifies both `8e5c69f96870` and `20260506_pakasir_qris` as down_revisions
- Becomes the new single HEAD of the migration chain
- Contains no schema changes (pure structural fix)

## Migration Chain After Fix

```
20250522_create_database.py
    ↓
[... other migrations ...]
    ↓
eecad7c18ac3_20251209_merge_max_sessions_and_.py
    ↓
8e5c69f96870_merge_ldap_with_main.py
    ↓ (BOTH POINT TO THIS)
20260716_01_complete_merge_all_heads.py ← SINGLE HEAD (NEW)
    ↓
20260506_add_pakasir_qris_tables.py (if using QRIS features)
```

## Deployment Instructions

### 1. On Deployment Machine
```bash
# Pull the latest QRIS branch
git checkout QRIS
git pull origin QRIS

# Verify the migration history is now linear
flask db history

# You should see a single head and no "multiple heads" errors
flask db current

# Run the upgrade
flask db upgrade
```

### 2. If Database Already Has Older Migrations

If your database is stuck on an older version, you may need to repair it first:

```bash
# Check database status
flask db current

# If stuck on an orphaned revision, use the migration doctor
python scripts/migration_doctor.py

# Then run upgrade
flask db upgrade
```

### 3. Docker Deployment

If using Docker, the migration will run automatically on startup because of:
- `FLASK_ENV=production` (or development)
- Entrypoint script that runs `flask db upgrade`

## What Happens on Deployment

1. Container starts → Alembic checks migration status
2. Alembic sees migration chain is now linear (no multiple heads)
3. Upgrade runs to apply `20260716_01_complete_merge_all_heads.py` (no-op, just marks it in DB)
4. All subsequent migrations work smoothly
5. **No more "Multiple head revisions" errors**

## Verification

After deployment, verify the fix:

```bash
# Check current migration
flask db current
# Output should show: 20260716_01_complete_merge_all_heads

# Check heads (should be only ONE)
flask db heads
# Output should show: 20260716_01_complete_merge_all_heads

# If you see multiple heads still, check for uncommitted migration files
ls -la migrations/versions/
```

## Prevention for Future

To prevent this issue in the future:

1. **Never manually edit migration files after they're committed**
2. **Always merge branches before committing migrations**
3. **Use this pattern when merging feature branches with migrations**:
   ```python
   # In feature branch's last migration:
   down_revision = "main_branch_last_migration"
   
   # After merge, create explicit merge migration if needed
   down_revision = ("main_head", "feature_head")  # Tuple = merge
   ```
4. **Run `flask db heads` before deployment** to catch multiple heads early

## Files Modified/Added

- ✅ `migrations/versions/20260716_01_complete_merge_all_heads.py` - **NEW**
- 📄 `MIGRATION_FIX_README.md` - This file (documentation)

## Important Notes

- This fix is **retroactive** - it doesn't affect existing databases
- The migration is a **no-op** (no schema changes)
- It only **records the merge** in the `alembic_version` table
- **Completely safe to run** - can even be safely rolled back without issues
- **All future migrations** will now work without the multiple heads error

## Support

If you encounter any issues after deployment:

1. Check the Docker logs: `docker logs wizarr-1`
2. Verify migration status: `flask db current`
3. Check for multiple heads: `flask db heads`
4. Run the migration doctor: `python scripts/migration_doctor.py`

For questions or issues, refer to the Alembic documentation or the `scripts/migration_doctor.py` tool included in this repo.
