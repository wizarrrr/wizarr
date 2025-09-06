# CalVer Automation

Simple time-based calendar versioning for Wizarr with automated release management.

## How it works

1. **Automatic**: Runs on every push to `main`
2. **Time-based**: Uses `YYYY.M.PATCH` format (e.g., `2025.9.0` → `2025.9.1` → `2025.10.0`)
3. **PR-based**: Creates "Release vX.Y.Z" PRs with auto-generated changelog
4. **Manual merge**: You merge the PR when ready to release
5. **Auto-release**: Merging triggers GitHub release + Docker builds

## Version Logic

- **Same month**: Increment patch (`2025.9.0` → `2025.9.1`)  
- **New month**: Reset patch (`2025.9.5` → `2025.10.0`)
- **New year**: Reset patch (`2025.12.3` → `2026.1.0`)

## Files Updated

- `pyproject.toml` version field
- `package.json` version field  
- Auto-generated changelog from commit messages

## Testing

```bash
# Dry run (no PR creation)
gh workflow run calver-automation.yml -f dry-run=true

# Check logs
gh run list --workflow=calver-automation.yml
gh run view [RUN_ID] --log
```

## Manual Trigger

```bash
# Trigger workflow manually
gh workflow run calver-automation.yml
```

## Workflow Files

- `.github/workflows/calver-automation.yml` - Main workflow
- `.github/workflows/create-release.yml` - Release creation on PR merge
- `.github/actions/calver-automation/` - Custom action logic