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
        "@semantic-release/commit-analyzer",
        "@semantic-release/release-notes-generator",
        ["@semantic-release/changelog", {
            changelogFile: "CHANGELOG.md",
        }],
        ["@semantic-release/exec", {
            prepareCmd: "echo \"${nextRelease.version}\" > latest",
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
        "@wizarrrr/semantic-release-discord",
        "@semantic-release/github",
        ["@wizarrrr/semantic-release-sentry-releases", {
            sourcemaps: "dist/apps/wizarr-frontend"
        }]
    ]
}

module.exports = config;
