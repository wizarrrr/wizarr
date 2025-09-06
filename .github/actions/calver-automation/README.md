# CalVer Automation

Simple time-based calendar versioning for Wizarr with automated release management.

## How it works

1. **Automatic**: Runs on every push to `main`
2. **Time-based**: Uses `YYYY.M.PATCH` format (e.g., `2025.9.0` → `2025.9.1` → `2025.10.0`)
3. **Dual PR-based**: Creates TWO PRs for each release:
   - **RC PR**: `RC v2025.9.1-rc.1` (beta testing)
   - **Release PR**: `Release v2025.9.1` (production)
4. **Manual control**: You choose when to merge each PR
5. **RC workflow**: RC PR → Pre-release + beta Docker builds
6. **Release workflow**: Release PR → GitHub release + production Docker builds + auto-closes RC PR

## Version Logic

- **Same month**: Increment patch (`2025.9.0` → `2025.9.1`)  
- **New month**: Reset patch (`2025.9.5` → `2025.10.0`)
- **New year**: Reset patch (`2025.12.3` → `2026.1.0`)

## Files Updated

- `pyproject.toml` version field
- `package.json` version field  
- Auto-generated changelog from commit messages

## Configuration

### GitHub Token Setup
For PRs to trigger CI workflows (tests, linting), you need a personal access token:

1. Create a fine-grained PAT at https://github.com/settings/tokens?type=beta
2. Grant permissions: `Contents: Write`, `Pull Requests: Write`, `Actions: Write`
3. Add as repository secret: `RELEASE_PLEASE_TOKEN`

Without this token, PRs will use `GITHUB_TOKEN` and won't trigger CI workflows.

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

- `.github/workflows/calver-automation.yml` - Main workflow (creates dual PRs)
- `.github/workflows/rc-prerelease.yml` - Creates pre-releases when RC PRs merge
- `.github/workflows/create-release.yml` - Creates releases when Release PRs merge
- `.github/workflows/close-rc-on-release.yml` - Auto-closes RC PRs when Release PRs merge  
- `.github/workflows/release.yml` - Docker builds (separate jobs for beta vs production)
- `.github/actions/calver-automation/` - Custom action logic

## Release Workflow

### When you push to main:
```
CalVer Automation creates:
├── RC v2025.9.1-rc.1 PR    (beta testing)
└── Release v2025.9.1 PR    (production ready)
```

### When you're ~90% confident:
```
Merge RC PR →
├── GitHub pre-release created
├── Docker images: :beta, :rc, :v2025.9.1-rc.1  
└── Deploy to staging/beta for testing
```

### When you're 100% confident:
```
Merge Release PR →
├── GitHub release created
├── Docker images: :latest, :v2025.9.1
├── Deploy to production
└── Auto-close RC PR
```