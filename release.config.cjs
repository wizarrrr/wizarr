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
    branches: [
        "main",
        "master",
        { name: "beta", prerelease: true },
    ],
    plugins: [
        ["@semantic-release/exec", {
            // use semantic-release logger to print the branch name
            prepareCmd: "echo \"Branch: ${branch}\"",
        }],
        "@semantic-release/commit-analyzer",
        "@semantic-release/release-notes-generator",
        ["@semantic-release/changelog", {
            changelogFile: isBeta ? "CHANGELOG-beta.md" : "CHANGELOG.md",
        }],
        ["@semantic-release/exec", {
            prepareCmd: "echo \"${nextRelease.version}\" > latest",
        }],
        ["@semantic-release/git", {
            assets: [
                "CHANGELOG.md",
                "CHANGELOG-beta.md",
                "latest"
            ],
            message: "chore(release): ${nextRelease.version}\n\n${nextRelease.notes}",
        }],
        "@wizarrrr/semantic-release-discord",
        ["@wizarrrr/semantic-release-sentry-releases", {
            sourcemaps: "dist/apps/wizarr-frontend"
        }]
    ]
}

if (isMaster) {
    config.plugins.splice(-2, 0, "@semantic-release/github");
}

module.exports = config;
