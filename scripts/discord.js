const axios = require('axios');

// Find process argument where argName is --argName=argValue and return argValue
const getArgs = (argName) => {
    const arg = process.argv.find((arg) => arg.includes(`--${argName}=`));
    return arg ? arg.split('=')[1] : null;
}

console.log(getArgs('--version'));

// stderr output
console.error('Error sending Discord message:', error.message);

// // Get the Discord webhook URL from the secrets store
// const WEBHOOK_URL = process.env.WEBHOOK_URL;

// const discordPayload = {
//     content: "THIS IS A TEST MESSAGE, PLEASE IGNORE",
//     embeds: [
//         {
//             title: "🚀 New Beta Release [v2.0.0-beta.1] 🚀",
//             description: "We are excited to announce the release of **v2.0.0-beta.1** of our software! This beta release comes with the following changes. 🎉\n\nWhat's New in this Beta Release\n- **🌟 Feature 1:** Introducing a brand new user interface with a more intuitive design.\n- **⚡ Feature 2:** Improved performance and faster loading times.\n- **💻 Feature 3:** Enhanced compatibility with various operating systems.\n- **🐞 Feature 4:** Bug fixes and stability improvements based on your valuable feedback.\n\nHow to Get the Beta Release\nTo access the beta release, simply pull the latest copy of our Beta Docker Image. Your feedback on the beta is crucial to helping us make this release even better, so please don't hesitate to reach out with any comments, questions, or bug reports.\n\nThank you for being a part of our beta testing community, and we look forward to your feedback to make this release a success! 🙌\n\nHappy testing! 🧪",
//             url: "https://github.com/Wizarrrr/wizarr/releases/tag/v3.5.0-v3-beta.9",
//             color: 16728405,
//             author: {
//                 name: "Wizarr Github",
//                 url: "https://github.com/Wizarrrr/wizarr",
//                 icon_url: "https://avatars.githubusercontent.com/u/113373916"
//             },
//             footer: {
//                 text: "Wizarr Team"
//             },
//             timestamp: new Date().toISOString(),
//         }
//     ],
//     attachments: []
// };

// const sendDiscordMessage = async () => {
//     try {
//         const response = await axios.post(process.env.WEBHOOK_URL, discordPayload);
//         console.log('Discord message sent:', response.status, response.statusText);
//     } catch (error) {
//         console.error('Error sending Discord message:', error.message);
//         process.exit(1);
//     }
// };

// sendDiscordMessage();

// Exit with a non-zero exit code if the message was not sent
process.exit(0);