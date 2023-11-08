const getCommitPatchSet = require('./diff-tree.cjs')
const path = require('path')

/**
 * @typedef {import('./types').Config} Config
 * @typedef {import('./types').Context} Context
 * @typedef {import('./types').SentryReleaseCommit} SentryReleaseCommit
 */

/**
 * @param {Config} pluginConfig -.
 * @param {Context} ctx -.
 * @returns {Promise<Array<SentryReleaseCommit>>} -.
 * @example
 * const commits = await parseCommits(ctx)
 */
const parseCommits = async (pluginConfig, ctx) => {
    /** @type {Array<SentryReleaseCommit>} */
    const commits = []
    for (const commit of ctx.commits) {
        /** @type {SentryReleaseCommit} */
        const releaseCommit = {
            id: commit.hash,
            message: commit.message,
            author_name: commit.author.name,
            author_email: commit.author.email,
            timestamp: commit.committerDate,
            repository: pluginConfig.repositoryUrl,
        }
        releaseCommit.patch_set = await getCommitPatchSet(
            pluginConfig.pathToGitFolder
                ? path.resolve(ctx.cwd, pluginConfig.pathToGitFolder)
                : ctx.cwd,
            releaseCommit.id,
        )
        commits.push(releaseCommit)
    }
    return commits
}

module.exports = parseCommits
