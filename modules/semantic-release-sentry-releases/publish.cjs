const path = require('path')
const getError = require('./get-error.cjs')
const parseCommits = require('./parse-commits.cjs')
const getAssets = require('./get-assets.cjs')
const { createRelease, createDeploy, uploadSourceFiles, getRepositoryName } = require('./request.cjs')

/**
 * @typedef {import('./types').Context} Context
 * @typedef {import('./types').Config} Config
 * @typedef {import('./types').PublishResult} PublishResult
 * @typedef {import('./types').SentryReleaseParams} SentryReleaseParams
 * @typedef {import('./types').SentryDeployParams} SentryDeployParams
 */

/**
 * @param {Config} pluginConfig -.
 * @param {Context} ctx -.
 * @returns {SentryDeployParams} -.
 * @example
 * getDeployData(pluginConfig, ctx)
 */
const getDeployData = (pluginConfig, ctx) => {
    /** @type {SentryDeployParams} */
    const deployData = {
        environment:
            ctx.env.SENTRY_ENVIRONMENT || pluginConfig.environment || 'production',
    }
    if (pluginConfig.deployName) {
        deployData.name = pluginConfig.deployName
    }
    if (pluginConfig.deployUrl) {
        deployData.url = pluginConfig.deployUrl
    }
    if (ctx.env.DEPLOY_START) {
        deployData.dateStarted = ctx.env.DEPLOY_START
    }
    if (ctx.env.DEPLOY_END) {
        deployData.dateStarted = ctx.env.DEPLOY_END
    }
    return deployData
}

/**
 * @param {Config} pluginConfig -.
 * @param {Context} ctx -.
 * @returns {Promise<PublishResult>} -.
 * @example
 * publish(pluginConfig, ctx)
 */
module.exports = async (pluginConfig, ctx) => {
    try {
        const tagsUrl = pluginConfig.tagsUrl || ''
        const project = ctx.env.SENTRY_PROJECT || pluginConfig.project
        const org = ctx.env.SENTRY_ORG || pluginConfig.org
        const url = ctx.env.SENTRY_URL || pluginConfig.url || 'https://sentry.io/'
        ctx.logger.log('Retrieving repository name')
        pluginConfig.repositoryUrl = await getRepositoryName(
            ctx.env.SENTRY_AUTH_TOKEN,
            org,
            url,
            pluginConfig.repositoryUrl || ctx.options.repositoryUrl,
        )
        ctx.logger.log('Retrieving commits data')
        const commits = await parseCommits(pluginConfig, ctx)
        ctx.logger.log('Commit data retrieved')
        const sentryReleaseVersion = pluginConfig.releasePrefix
            ? `${pluginConfig.releasePrefix}-${ctx.nextRelease.version}`
            : ctx.nextRelease.version
        const projectsArray = /\s/g.test(project) ? project.split(/\s/g) : [project]
        /** @type {SentryReleaseParams} */
        const releaseDate = {
            commits,
            version: sentryReleaseVersion,
            projects: projectsArray,
        }
        if (tagsUrl !== '') {
            releaseDate.url = `${tagsUrl}/v${ctx.nextRelease.version}`
        }
        ctx.logger.log('Creating release %s', sentryReleaseVersion)
        const release = await createRelease(
            releaseDate,
            ctx.env.SENTRY_AUTH_TOKEN,
            org,
            url,
        )
        ctx.logger.log('Release created')
        process.env.SENTRY_ORG = org
        process.env.SENTRY_URL = url
        process.env.SENTRY_PROJECT = project
        if (pluginConfig.sourcemaps && pluginConfig.urlPrefix) {
            const sourcemaps = path.resolve(ctx.cwd, pluginConfig.sourcemaps)
            ctx.logger.log('Searching sourcemaps in %s', sourcemaps)
            const assets = await getAssets(
                pluginConfig.sourcemaps,
                pluginConfig.urlPrefix,
            )
            ctx.logger.log('Uploading sourcemaps from %s', sourcemaps)
            await uploadSourceFiles(
                assets,
                pluginConfig.rewrite || false,
                ctx.env.SENTRY_AUTH_TOKEN,
                org,
                url,
                sentryReleaseVersion,
            )
            ctx.logger.log('Sourcemaps uploaded')
        }
        const deployData = getDeployData(pluginConfig, ctx)
        ctx.logger.log('Creating deploy for release %s', sentryReleaseVersion)
        const deploy = await createDeploy(
            deployData,
            ctx.env.SENTRY_AUTH_TOKEN,
            org,
            url,
            sentryReleaseVersion,
        )
        ctx.logger.log('Deploy created')
        return { release, deploy }
    } catch (err) {
        ctx.logger.error(err)
        throw getError('ESENTRYDEPLOY', ctx)
    }
}
