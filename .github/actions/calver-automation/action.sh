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
    local last_release_tag

    # Get the latest ACTUAL release tag (not RC or pre-release)
    # Sort by version and get the latest non-pre-release tag
    last_release_tag=$(git tag -l | grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1 2>/dev/null || echo "")

    if [[ -z "$last_release_tag" ]]; then
        # No previous release tag, get all commits
        git log --oneline --no-merges
    else
        # Get commits since last actual release (not RC/beta)
        git log "${last_release_tag}..HEAD" --oneline --no-merges
    fi
}

# Generate changelog with improved conventional commit detection
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

    # Group commits by type with more comprehensive detection
    local features=""
    local fixes=""
    local docs=""
    local perf=""
    local refactor=""
    local test=""
    local build=""
    local ci=""
    local style=""
    local chore=""
    local breaking=""
    local other=""

    while IFS= read -r line; do
        local commit_hash=$(echo "$line" | cut -d' ' -f1)
        local commit_full_msg=$(echo "$line" | sed 's/^[a-f0-9]* //')

        # Check for breaking changes first (can be any type)
        if echo "$commit_full_msg" | grep -qE "(BREAKING CHANGE|!):"; then
            breaking+="- $commit_full_msg\n"
        # Features
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ feat(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* feat[^:]*: *//')
            features+="- $commit_msg\n"
        # Bug fixes
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ fix(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* fix[^:]*: *//')
            fixes+="- $commit_msg\n"
        # Documentation
        elif echo "$line" | grep -qE "^[a-f0-9]+ docs(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-f0-9]* docs[^:]*: *//')
            docs+="- $commit_msg\n"
        # Performance improvements
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ perf(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* perf[^:]*: *//')
            perf+="- $commit_msg\n"
        # Code refactoring
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ refactor(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* refactor[^:]*: *//')
            refactor+="- $commit_msg\n"
        # Testing
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ test(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* test[^:]*: *//')
            test+="- $commit_msg\n"
        # Build system / dependencies
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ (build|deps?)(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* \(build\|deps\?\)[^:]*: *//')
            build+="- $commit_msg\n"
        # CI/CD changes
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ ci(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* ci[^:]*: *//')
            ci+="- $commit_msg\n"
        # Code style changes
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ style(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* style[^:]*: *//')
            style+="- $commit_msg\n"
        # Chores and maintenance
        elif echo "$line" | grep -qE "^[a-fA-F0-9]+ chore(\([^)]+\))?(!)?:"; then
            local commit_msg=$(echo "$line" | sed 's/^[a-fA-F0-9]* chore[^:]*: */')
            chore+="- $commit_msg\n"
        # Non-conventional commits
        else
            other+="- $commit_full_msg\n"
        fi
    done <<< "$commits"

    # Output sections in priority order
    if [[ -n "$breaking" ]]; then
        echo "### 💥 Breaking Changes"
        echo -e "$breaking"
    fi

    if [[ -n "$features" ]]; then
        echo "### 🚀 Features"
        echo -e "$features"
    fi

    if [[ -n "$fixes" ]]; then
        echo "### 🐛 Bug Fixes"
        echo -e "$fixes"
    fi

    if [[ -n "$perf" ]]; then
        echo "### ⚡ Performance Improvements"
        echo -e "$perf"
    fi

    if [[ -n "$refactor" ]]; then
        echo "### ♻️ Code Refactoring"
        echo -e "$refactor"
    fi

    if [[ -n "$docs" ]]; then
        echo "### 📚 Documentation"
        echo -e "$docs"
    fi

    if [[ -n "$test" ]]; then
        echo "### 🧪 Tests"
        echo -e "$test"
    fi

    if [[ -n "$build" ]]; then
        echo "### 🔧 Build System / Dependencies"
        echo -e "$build"
    fi

    if [[ -n "$ci" ]]; then
        echo "### 👷 CI/CD"
        echo -e "$ci"
    fi

    if [[ -n "$style" ]]; then
        echo "### 💄 Styling"
        echo -e "$style"
    fi

    if [[ -n "$chore" ]]; then
        echo "### 🧹 Chores"
        echo -e "$chore"
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
    local commit_summary
    commit_summary=$(generate_commit_summary)

    local pr_body="# 🧪 Release Candidate v$rc_version

$changelog

$commit_summary

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

# Generate detailed commit summary for PR
generate_commit_summary() {
    local commits
    commits=$(get_commits_since_last_release)

    if [[ -z "$commits" ]]; then
        echo "No commits found."
        return
    fi

    local commit_count=$(echo "$commits" | wc -l)
    echo "## 📋 All Commits Included ($commit_count commits)"
    echo ""

    # Show each commit with hash for reference
    echo "<details>"
    echo "<summary>Click to expand commit list</summary>"
    echo ""
    echo "\`\`\`"
    while IFS= read -r line; do
        echo "$line"
    done <<< "$commits"
    echo "\`\`\`"
    echo "</details>"
    echo ""
}

# Create or update release PR
create_release_pr() {
    local version="$1"
    local changelog="$2"
    local existing_pr="$3"

    local pr_title="Release v$version"
    local commit_summary
    commit_summary=$(generate_commit_summary)

    local pr_body="# 🚀 Stable Release v$version

$changelog

$commit_summary

---

## Stable Release

**Merge this PR when**: You're ready for production deployment

**This will**:
- Create GitHub release \`v$version\`
- Deploy to production
- Build Docker images with \`:latest\` and \`v$version\` tags
- Notify stakeholders

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

# Update existing release PR description with latest changelog
update_existing_release_pr() {
    local branch_name="$1"

    # Extract version from branch name (release/v2025.9.6 -> 2025.9.6)
    local version
    version=$(echo "$branch_name" | sed 's/release\/v//')

    log_info "Updating Release PR for version: $version"

    # Find the existing release PR for this version
    local existing_pr
    existing_pr=$(check_existing_pr "Release v$version")

    if [[ -z "$existing_pr" ]]; then
        log_warning "No existing Release PR found for v$version"
        echo "release-created=false" >> "$GITHUB_OUTPUT"
        return 0
    fi

    # Generate fresh changelog with latest commits
    local changelog
    changelog=$(generate_changelog "$version")

    # Update the PR with fresh content
    create_release_pr "$version" "$changelog" "$existing_pr"

    log_success "Updated Release PR #$existing_pr with latest changelog"

    # Set outputs
    echo "release-created=true" >> "$GITHUB_OUTPUT"
    echo "tag-name=v$version" >> "$GITHUB_OUTPUT"
    echo "pr-number=$existing_pr" >> "$GITHUB_OUTPUT"
}

# Main execution
main() {
    log_info "Starting CalVer Automation..."

    # Set up git config
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"

    # Check if we're on a release branch - if so, just update the PR
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" == release/* ]]; then
        log_info "Running on release branch: $current_branch"
        update_existing_release_pr "$current_branch"
        return 0
    fi

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
    
    # Check for existing Release PR
    local existing_release_pr
    existing_release_pr=$(check_existing_pr "Release v")
    
    # Create Release branch and PR (stable release only)
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
    
    log_success "Release PR ready: #$release_pr_number"
    
    # Set outputs
    echo "release-created=true" >> "$GITHUB_OUTPUT"
    echo "tag-name=v$next_version" >> "$GITHUB_OUTPUT"
    echo "pr-number=$release_pr_number" >> "$GITHUB_OUTPUT"
}

# Run main function
main "$@"