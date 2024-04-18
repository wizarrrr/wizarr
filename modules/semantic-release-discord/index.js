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
        markdownText = markdownText.replace(/.*?##/s, '##');
        markdownText = markdownText.substring(headerIndex);
        markdownText = markdownText.replace(/^\s*\n/gm, '');
        markdownText = markdownText.replace(/^(#+)\s*(.*?)\s*$/gm, '*$2*');
        return markdownText;
    }

    // Check if version is a beta release
    const isBeta = version.includes("beta");

    const discordPayload = {
        embeds: [
            {
                title: `🚀 New ${isBeta ? "Beta" : ""} Release [${version}] 🚀`,
                description: 'We are excited to announce the release of **${version}**! This ${isBeta ? "beta" : ""} release comes with the following changes: \n\n**What has Changed in this ${isBeta ? "Beta" : ""} Release?**\n${parseNotes(notes)}\n**How to Get the ${isBeta ? "Beta" : ""} Release**\nTo access the ${isBeta ? "beta" : ""} release, simply use ${isBeta ? "```ghcr.io/wizarrrr/wizarr:beta```" : "```ghcr.io/wizarrrr/wizarr:latest```"} as your image tag. Your feedback is crucial to helping us make each release even better, so please do not hesitate to reach out with any comments, questions, or bug reports.\n\n${isBeta ? "Happy testing! 🧪" : "Happy updating! 🎉"}${isBeta ? "\n\n<@&1150177174167494826>" : ""}',
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
