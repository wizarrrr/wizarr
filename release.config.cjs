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
        ["@semantic-release/git", {
            assets: ["./dist/**/*.{js,css}"],
            message: "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}",
        }],
        "@semantic-release/github"
    ]
}

module.exports = config;
