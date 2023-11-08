const github = require('@actions/github');

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
    const { nextRelease, logger } = context;

    // Get the Octokit client using the provided GitHub token
    const octokit = github.getOctokit(pluginConfig.githubToken)

    // Create a dispatch event
    octokit.rest.repos.createDispatchEvent({
        owner: pluginConfig.owner,
        repo: pluginConfig.repo,
        event_type: pluginConfig.eventName,
        client_payload: {
            version: pluginConfig.payload.version || nextRelease.gitTag,
            image: pluginConfig.payload.image,
            branch: pluginConfig.payload.branch
        }
    });

    // Log the success
    logger.log("Dispatched GitHub event with event type: " + pluginConfig.eventName);
}

module.exports = { publish }