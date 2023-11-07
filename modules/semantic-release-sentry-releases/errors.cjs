/* eslint-disable sonarjs/no-duplicate-string */
// @ts-ignore
const pkg = require('./package.json')

const [homepage] = pkg.homepage.split('#')
/**
 * @param {string} file -.
 * @returns {string} -.
 * @example
 * const link = linkify(href)
 */
const linkify = (file) => `${homepage}/blob/master/${file}`

/**
 * @typedef {import('./types').Context} Context
 */
/**
 * @typedef {Object} SemanticReleaseError
 * @property {string} message -.
 * @property {string} details -.
 */

module.exports = new Map([
    [
        'ENOSENTRYTOKEN',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: 'No sentry token specified.',
            details: `An [sentry token](${linkify(
                'README.md#environment-variables',
            )}) must be created and set in the \`SENTRY_AUTH_TOKEN\` environment variable on your CI environment.


Please make sure to create an [sentry token](https://docs.sentry.io/api/auth/#id1) and to set it in the \`SENTRY_AUTH_TOKEN\` environment variable on your CI environment. The token must allow to create relases.`,
        }),
    ],
    [
        'ENOSENTRYORG',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: 'No sentry org specified.',
            details: `An [sentry org](${linkify(
                'README.md#environment-variables',
            )}) must be created and set in the \`SENTRY_ORG\` environment variable on your CI environment or set org in plugin config.`,
        }),
    ],
    [
        'ENOSENTRYPROJECT',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: 'No sentry project specified.',
            details: `An [sentry project](${linkify(
                'README.md#environment-variables',
            )}) must be created and set in the \`SENTRY_PROJECT\` environment variable on your CI environment or set project in plugin config.`,
        }),
    ],
    [
        'EINVALIDTAGSURL',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: 'Invalid tags url.',
            details: `The [tagsUrl option](${linkify(
                'README.md#options',
            )}), if defined, must be a valid url.`,
        }),
    ],
    [
        'EINVALIDSENTRYURL',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: 'Invalid sentry url.',
            details: `The [url option](${linkify(
                'README.md#options',
            )}), if defined, must be a valid url.`,
        }),
    ],
    [
        'EINVALIDSENTRYTOKEN',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: ctx.message || 'Invalid token.',
            details: `The [sentry token](${linkify(
                'README.md#environment-variables',
            )}) configured in the \`SENTRY_AUTH_TOKEN\` environment variable must be a valid [token](https://docs.sentry.io/api/auth/#id1) allowing to list and create releases to org \`${ctx.env.SENTRY_ORG
                }\`.
Please make sure to set the \`SENTRY_AUTH_TOKEN\` environment variable in your CI with the exact value of the sentry token.`,
        }),
    ],
    [
        'EPERMISSIONSSENTRYTOKEN',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message:
                ctx.message || 'You do not have permission to perform this action.',
            details: `The [sentry token](${linkify(
                'README.md#environment-variables',
            )}) configured in the \`SENTRY_AUTH_TOKEN\` environment variable must be [token](https://docs.sentry.io/api/auth/#id1) with permissions to list and create releases to org \`${ctx.env.SENTRY_ORG
                }\`.
Please make sure to set the \`SENTRY_AUTH_TOKEN\` environment variable in your CI with the exact value of the sentry token.`,
        }),
    ],
    [
        'EINVALIDSENTRYORG',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: ctx.message || 'The requested resource does not exist.',
            details: `The [sentry org](${linkify(
                'README.md#environment-variables',
            )}) configured in the \`SENTRY_ORG\` environment variable must be a valid org slug. Current org is \`${ctx.env.SENTRY_ORG
                }\`.
Please make sure to set the \`SENTRY_ORG\` environment variable in your CI with the exact value of the sentry org.`,
        }),
    ],
    [
        'ESENTRYDEPLOY',
        /**
         * @param {Context} ctx -.
         * @returns {SemanticReleaseError} -.
         */
        (ctx) => ({
            message: 'Error in new release request.',
            details: 'Check the [sentry status](https://status.sentry.io/)',
        }),
    ],
])
/* eslint-enable sonarjs/no-duplicate-string */
