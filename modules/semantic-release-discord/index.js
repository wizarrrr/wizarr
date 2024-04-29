const resolveConfig = require('./resolve-config');
const axios = require('axios');

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
const success = (pluginConfig, context) => {

    const config = resolveConfig(pluginConfig, context);
    const { nextRelease, logger } = context;

    const version = nextRelease.name;
    const webhookUrl = config.webhookUrl;
    const notes = nextRelease.notes;
    const url = `https://github.com/Wizarrrr/wizarr/releases/tag/${version}`;

    const parseNotes = (markdownText) => {
        const headerIndex = markdownText.search(/#+\s/);
        markdownText = markdownText.replace(/.*?##/s, "##");
        markdownText = markdownText.substring(headerIndex);
        markdownText = markdownText.replace(/^\s*\n/gm, "");
        markdownText = markdownText.replace(/^(#+)\s*(.*?)\s*$/gm, "*$2*");
        return markdownText;
    };

    // Check if version is a beta release
    const isBeta = version.includes("beta");

    const discordPayload = {
        content: `${isBeta ? "<@&1141148163558887495>" : "<@&1150177174167494826>"}`,
        embeds: [
            {
                title: `🚀 New ${isBeta ? "Beta" : ""} Release [${version}] 🚀`,
                description: `We are excited to announce the release of **${version}**! This ${isBeta ? "beta" : ""} release comes with the following changes: \n\n**What\'s changed in this ${isBeta ? "beta" : ""} release?**\n${parseNotes(notes)}\n**How can you get the ${isBeta ? "beta" : ""} release?**\nTo access the ${isBeta ? "beta" : ""} release, simply use \`ghcr.io/wizarrrr/wizarr:${isBeta ? "beta" : "latest"}\` as your image tag and re-create your container, pulling the updated image. Your feedback is crucial to helping us make each release even better, so please don\'t hesitate to reach out with any comments, questions, or bug reports.\n\n${isBeta ? "Happy testing! 🧪" : "Happy updating! 🎉"}`,
                url: url,
                color: 16728405,
                author: {
                    name: "Wizarr Github",
                    url: "https://github.com/Wizarrrr/wizarr",
                    icon_url: "https://avatars.githubusercontent.com/u/113373916",
                },
                footer: {
                    text: "Wizarr Team",
                },
                timestamp: new Date().toISOString(),
            },
        ],
        attachments: [],
    };

    try {
        axios.post(webhookUrl, discordPayload);
        logger.log("Successfully sent Discord message.")
    } catch (error) {
        logger.error("Error sending Discord message:", error.message);
        throw error;
    }
}

module.exports = { success }
