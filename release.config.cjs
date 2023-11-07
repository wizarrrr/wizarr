/**
 * @type {import("semantic-release").GlobalConfig}
 */
const config = {
    branches: [
        "(\\d+)(\\.\\d+)?\\.x",
        "main",
        "master",
        { name: "v3-beta", prerelease: true },
    ],
    plugins: [
        "@semantic-release/commit-analyzer",
        "@semantic-release/release-notes-generator",
        ["@semantic-release/changelog", {
            changelogFile: "CHANGELOG.md",
        }],
        ["@semantic-release/exec", {
            prepareCmd: "echo \"${nextRelease.version}\" | sed 's/-.*//' > latest",
        }],
        ["@semantic-release/exec", {
            prepareCmd: "node scripts/discord.js --version=${nextRelease.version}",
        }],
        ["@semantic-release/git", {
            assets: [
                "CHANGELOG.md",
                "package.json",
                "package-lock.json",
                "npm-shrinkwrap.json",
                "latest"
            ],
            message: "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}",
        }],
        "@semantic-release/github",
        ["@wizarrrr/semantic-release-sentry-releases", {
            sourcemaps: "dist/apps/wizarr-frontend"
        }]
    ]
}

module.exports = config;
