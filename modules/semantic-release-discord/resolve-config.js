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
function resolveConfig({ webhookUrl }, { env }) {
    return {
        webhookUrl: webhookUrl || env.DISCORD_WEBHOOK,
    }
}

module.exports = resolveConfig;