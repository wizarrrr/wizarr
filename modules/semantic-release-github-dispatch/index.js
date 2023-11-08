const core = require('@actions/core');
const github = require('@actions/github');
const resolveConfig = require('./resolve-config');

/**
 * @typedef {import('./types').Context} Context
 * @typedef {import('./types').Config} Config
 */

/**
 * @param {Config} pluginConfig -.
 * @param {Context} context -.
 * @example
 * success(pluginConfig, context)
 */
const publish = (pluginConfig, context) => {
    // Resolve the plugin configuration
    const config = resolveConfig(pluginConfig, context)
    const { nextRelease, logger } = context;

    // Get the Octokit client using the provided GitHub token
    const octokit = github.getOctokit(config.githubToken)

    // Create a dispatch event
    octokit.rest.repos.createDispatchEvent({
        owner: config.owner,
        repo: config.repo,
        event_type: config.eventName,
        client_payload: {
            version: config.payload.version || nextRelease.gitTag,
            image: config.payload.image,
            branch: config.payload.branch
        }
    });

    // Log the success
    logger.log("Dispatched GitHub event with event type: " + config.eventName);
}

module.exports = { publish }