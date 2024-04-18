// Store the current branch in a variable
const branch = process.env.CURRENT_BRANCH || "master";

if (!branch) {
    throw new Error("CURRENT_BRANCH not set");
}

const isBeta = branch === "beta";
const isMaster = branch === "master" || branch === "main";

/**
 * @type {import("semantic-release").GlobalConfig}
 */
const config = {
    branches: ["main", "master", { name: "beta", prerelease: true }],
    plugins: [
        [
            "@semantic-release/exec",
            {
                // use semantic-release logger to print the branch name
                prepareCmd: 'echo "Branch: ${branch}"',
            },
        ],
        [
            "@semantic-release/commit-analyzer",
            {
                // Modify default release rules to include types that are not breaking change, feat, or fix as a patch release
                // Default rules: https://github.com/semantic-release/commit-analyzer/blob/master/lib/default-release-rules.js
                releaseRules: [
                    {
                        scope: "no-release",
                        release: false,
                    },
                    {
                        type: "build",
                        release: "patch",
                    },
                    {
                        type: "ci",
                        release: "patch",
                    },
                    {
                        type: "chore",
                        release: "patch",
                    },
                    {
                        type: "docs",
                        release: "patch",
                    },
                    {
                        type: "refactor",
                        release: "patch",
                    },
                    {
                        type: "style",
                        release: "patch",
                    },
                    // {
                    //     type: "test",
                    //     release: "patch",
                    // },
                ],
            },
        ],
        [
            "@semantic-release/release-notes-generator",
            {
                preset: "conventionalcommits",
                presetConfig: {
                    types: [
                        { type: "feat", section: "New Features" },
                        { type: "fix", section: "Bug Fixes" },
                        { type: "perf", section: "Performance Improvements", hidden: false },
                        { type: "revert", section: "Commit Reverts", hidden: false },
                        { type: "build", section: "Build System", hidden: false },
                        { type: "ci", section: "Continuous Integration", hidden: false },
                        { type: "chore", section: "Chores", hidden: false },
                        { type: "docs", section: "Documentation", hidden: false },
                        { type: "style", section: "Style Changes", hidden: false },
                        { type: "refactor", section: "Code Refactoring", hidden: false },
                        { type: "test", section: "Test Cases", hidden: true },
                    ],
                },
            },
        ],
        [
            "@semantic-release/changelog",
            {
                changelogFile: isBeta ? "CHANGELOG-beta.md" : "CHANGELOG.md",
            },
        ],
        [
            "@semantic-release/exec",
            {
                prepareCmd: 'echo "${nextRelease.version}" > latest',
            },
        ],
        [
            "@semantic-release/git",
            {
                assets: ["CHANGELOG.md", "CHANGELOG-beta.md", "latest"],
                message: "chore(release): ${nextRelease.version}\n\n${nextRelease.notes}",
            },
        ],
        "@wizarrrr/semantic-release-discord",
        [
            "@wizarrrr/semantic-release-sentry-releases",
            {
                sourcemaps: "dist/apps/wizarr-frontend",
            },
        ],
    ],
};

if (isMaster) {
    config.plugins.splice(-2, 0, "@semantic-release/github");
}

module.exports = config;
