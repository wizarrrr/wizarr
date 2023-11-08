/**
 * @typedef {import('./types').Context} Context
 * @typedef {import('./types').Config} Config
 */

/**
 * @param {Config} pluginConfig -.
 * @param {Context} context -.
 * @returns {Config} -.
 * @example
 * resolveConfig(pluginConfig, context)
 */
function resolveConfig({ githubToken, eventName, payload }, { env }) {
    return {
        owner: owner || env.GITHUB_OWNER,
        repo: repo || env.GITHUB_REPO,
        githubToken: githubToken || env.GITHUB_TOKEN,
        eventName: eventName || env.GITHUB_EVENT_NAME,
        payload: {
            version: payload.version,
            image: payload.image,
            branch: payload.branch || env.CURRENT_BRANCH
        }
    }
}

module.exports = resolveConfig;