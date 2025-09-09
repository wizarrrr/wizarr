#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" >&2
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Get current version from pyproject.toml
get_current_version() {
    grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/'
}

# Calculate next CalVer version (YYYY.M.PATCH)
calculate_next_version() {
    local current_version="$1"
    local current_year=$(date +%Y)
    local current_month=$(date +%-m)  # No leading zero
    
    # Parse current version (strip any -rc.X or -beta suffixes)
    local version_year=$(echo "$current_version" | cut -d'.' -f1)
    local version_month=$(echo "$current_version" | cut -d'.' -f2)
    local version_patch=$(echo "$current_version" | cut -d'.' -f3 | sed 's/-.*$//')  # Strip -rc.1 or -beta suffixes
    
    log_info "Current: $current_version (Year: $version_year, Month: $version_month, Patch: $version_patch)"
    log_info "Today: $current_year.$current_month"
    
    if [[ "$current_year" -gt "$version_year" ]] || [[ "$current_year" -eq "$version_year" && "$current_month" -gt "$version_month" ]]; then
        # New month/year - reset patch to 0
        echo "$current_year.$current_month.0"
    else
        # Same month - increment patch
        local next_patch=$((version_patch + 1))
        echo "$current_year.$current_month.$next_patch"
    fi
}

# Get commits since last release
get_commits_since_last_release() {
    local last_tag
    last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    
    if [[ -z "$last_tag" ]]; then
        # No previous tag, get all commits
        git log --oneline --no-merges
    else
        # Get commits since last tag
        git log "${last_tag}..HEAD" --oneline --no-merges
    fi
}

# Generate changelog
generate_changelog() {
    local version="$1"
    local commits
    commits=$(get_commits_since_last_release)
    
    if [[ -z "$commits" ]]; then
        echo "No changes since last release."
        return
    fi
    
    echo "## What's Changed"
    echo ""
    
    # Group commits by type
    local features=""
    local fixes=""
    local other=""
    
    while IFS= read -r line; do
        if echo "$line" | grep -qE "^[a-f0-9]+ feat(\([^)]+\))?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-f0-9]* feat[^:]*: *//')
            features+="- $commit_msg\n"
        elif echo "$line" | grep -qE "^[a-f0-9]+ fix(\([^)]+\))?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-f0-9]* fix[^:]*: *//')
            fixes+="- $commit_msg\n"
        elif ! echo "$line" | grep -qE "^[a-f0-9]+ (chore|docs|style|refactor|test|ci)(\([^)]+\))?:"; then
            # Skip maintenance commits, include everything else
            local commit_msg=$(echo "$line" | sed 's/^[a-f0-9]* //')
            other+="- $commit_msg\n"
        fi
    done <<< "$commits"
    
    if [[ -n "$features" ]]; then
        echo "### 🚀 Features"
        echo -e "$features"
    fi
    
    if [[ -n "$fixes" ]]; then
        echo "### 🐛 Bug Fixes" 
        echo -e "$fixes"
    fi
    
    if [[ -n "$other" ]]; then
        echo "### 📝 Other Changes"
        echo -e "$other"
    fi
    
    echo ""
    echo "**Full Changelog**: https://github.com/$GITHUB_REPOSITORY/compare/v$(get_current_version)...v$version"
}

# Update version in files
update_version_files() {
    local new_version="$1"
    
    # Update pyproject.toml
    sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml # commitizen section too
    
    # Update package.json
    jq --arg version "$new_version" '.version = $version' package.json > package.json.tmp && mv package.json.tmp package.json
    
    # Clean up backup files
    rm -f pyproject.toml.bak
    
    log_success "Updated version files to $new_version"
}

# Check if release PR exists
check_existing_pr() {
    local search_term="$1"
    local pr_number
    pr_number=$(gh pr list --state open --search "$search_term" --json number --jq '.[0].number // empty' 2>/dev/null || echo "")
    echo "$pr_number"
}

# Create RC PR
create_rc_pr() {
    local version="$1"
    local changelog="$2"
    local existing_pr="$3"
    
    local rc_version="${version}-rc.1"
    local pr_title="RC v$rc_version"
    local pr_body="# 🧪 Release Candidate v$rc_version

$changelog

---

## Beta Testing Phase

**Merge this PR when**: You're ~90% confident and ready for beta/staging deployment

**This will**:
- Create GitHub pre-release \`v$rc_version\`
- Deploy to staging/beta environment  
- Build Docker images with \`:rc\` and \`:beta\` tags
- Notify beta testers

**Next steps**: After beta validation, merge the main Release PR for production

---

🤖 Auto-generated by CalVer Automation"
    
    if [[ -n "$existing_pr" ]]; then
        log_info "Updating existing RC PR #$existing_pr"
        gh pr edit "$existing_pr" --title "$pr_title" --body "$pr_body"
        echo "$existing_pr"
    else
        log_info "Creating new RC PR"
        gh pr create --title "$pr_title" --body "$pr_body" --base main --label "release-candidate"
        gh pr list --state open --search "RC v" --json number --jq '.[0].number'
    fi
}

# Create or update release PR
create_release_pr() {
    local version="$1"
    local changelog="$2"
    local existing_pr="$3"
    
    local rc_version="${version}-rc.1"
    local pr_title="Release v$version"
    local pr_body="# 🚀 Production Release v$version

$changelog

---

## Production Release

**Merge this PR when**: You're 100% confident and ready for production

**This will**:
- Create GitHub release \`v$version\`
- Deploy to production
- Build Docker images with \`:latest\` and \`v$version\` tags
- Auto-close the corresponding RC PR
- Notify production stakeholders

**Beta testing**: Merge the RC PR first for beta deployment and testing

---

🤖 Auto-generated by CalVer Automation"
    
    if [[ -n "$existing_pr" ]]; then
        log_info "Updating existing Release PR #$existing_pr"
        gh pr edit "$existing_pr" --title "$pr_title" --body "$pr_body"
        echo "$existing_pr"
    else
        log_info "Creating new Release PR"
        gh pr create --title "$pr_title" --body "$pr_body" --base main --label "production-release"
        gh pr list --state open --search "Release v" --json number --jq '.[0].number'
    fi
}

# Main execution
main() {
    log_info "Starting CalVer Automation..."
    
    # Set up git config
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    
    local current_version
    current_version=$(get_current_version)
    log_info "Current version: $current_version"
    
    local next_version
    next_version=$(calculate_next_version "$current_version")
    log_info "Next version: $next_version"
    
    # Check if we need a release
    if [[ "$next_version" == "$current_version" ]]; then
        log_warning "No version bump needed (same month, no new commits)"
        echo "release-created=false" >> "$GITHUB_OUTPUT"
        return 0
    fi
    
    # Check for existing commits since last release
    local commits
    commits=$(get_commits_since_last_release)
    if [[ -z "$commits" ]]; then
        log_warning "No commits since last release"
        echo "release-created=false" >> "$GITHUB_OUTPUT"
        return 0
    fi
    
    # Generate changelog
    log_info "Generating changelog..."
    local changelog
    changelog=$(generate_changelog "$next_version")
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - Not creating PR"
        echo "Would create release v$next_version"
        echo "Changelog:"
        echo "$changelog"
        echo "release-created=false" >> "$GITHUB_OUTPUT"
        return 0
    fi
    
    # Check for existing PRs
    local existing_rc_pr existing_release_pr
    existing_rc_pr=$(check_existing_pr "RC v")
    existing_release_pr=$(check_existing_pr "Release v")
    
    # Create RC branch and PR
    local rc_version="${next_version}-rc.1"
    local rc_branch_name="release/v$rc_version"
    
    # Always reset RC branch to latest main to ensure it's up to date
    if git show-ref --verify --quiet "refs/heads/$rc_branch_name"; then
        git branch -D "$rc_branch_name"  # Delete existing branch
    fi
    git checkout -b "$rc_branch_name"  # Create fresh branch from latest main
    
    # Update version files for RC
    update_version_files "$rc_version"
    
    # Commit RC changes
    git add pyproject.toml package.json
    git commit -m "chore: release candidate v$rc_version" || true
    
    # Push RC branch
    git push origin "$rc_branch_name" --force
    
    # Create RC PR
    local rc_pr_number
    rc_pr_number=$(create_rc_pr "$next_version" "$changelog" "$existing_rc_pr")
    
    # Create Release branch and PR (with production version)
    local release_branch_name="release/v$next_version"
    
    git checkout main  # Start from main for release branch
    git pull origin main  # Ensure we have latest main
    
    # Always reset release branch to latest main to ensure it's up to date
    if git show-ref --verify --quiet "refs/heads/$release_branch_name"; then
        git branch -D "$release_branch_name"  # Delete existing branch
    fi
    git checkout -b "$release_branch_name"  # Create fresh branch from latest main
    
    # Update version files for release
    update_version_files "$next_version"
    
    # Commit release changes
    git add pyproject.toml package.json
    git commit -m "chore: release v$next_version" || true
    
    # Push release branch
    git push origin "$release_branch_name" --force
    
    # Create Release PR
    local release_pr_number
    release_pr_number=$(create_release_pr "$next_version" "$changelog" "$existing_release_pr")
    
    log_success "RC PR ready: #$rc_pr_number"
    log_success "Release PR ready: #$release_pr_number"
    
    # Set outputs
    echo "release-created=true" >> "$GITHUB_OUTPUT"
    echo "tag-name=v$next_version" >> "$GITHUB_OUTPUT"
    echo "pr-number=$release_pr_number" >> "$GITHUB_OUTPUT"
    echo "rc-pr-number=$rc_pr_number" >> "$GITHUB_OUTPUT"
}

# Run main function
main "$@"