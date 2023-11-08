const regex = [
    {
        regex: /(?<=^feat(\(.*\))?(:)?)\s/,
        emoji: ' ✨ '
    },
    {
        regex: /(?<=^fix(\(.*\))?(:)?)\s/,
        emoji: ' 🐛 '
    },
    {
        regex: /(?<=^docs(\(.*\))?(:)?)\s/,
        emoji: ' 📚 '
    },
    {
        regex: /(?<=^style(\(.*\))?(:)?)\s/,
        emoji: ' 💎 '
    },
    {
        regex: /(?<=^refactor(\(.*\))?(:)?)\s/,
        emoji: ' 📦 '
    },
    {
        regex: /(?<=^perf(\(.*\))?(:)?)\s/,
        emoji: ' 🚀 '
    },
    {
        regex: /(?<=^test(\(.*\))?(:)?)\s/,
        emoji: ' 🚨 '
    },
    {
        regex: /(?<=^build(\(.*\))?(:)?)\s/,
        emoji: ' 👷 '
    },
    {
        regex: /(?<=^ci(\(.*\))?(:)?)\s/,
        emoji: ' 💚 '
    },
    {
        regex: /(?<=^chore(\(.*\))?(:)?)\s/,
        emoji: ' 🔧 '
    },
    {
        regex: /(?<=^revert(\(.*\))?(:)?)\s/,
        emoji: ' ⏪ '
    },
    {
        regex: /(?<=^release(\(.*\))?(:)?)\s/,
        emoji: ' 🏹 '
    },
    {
        regex: /(?<=^dependabot(\(.*\))?(:)?)\s/,
        emoji: ' 📦 '
    },
    {
        regex: /(?<=^first(\(.*\))?(:)?)\s/,
        emoji: ' 🎉 '
    }
]

// Emojify a commit message
function emojifyCommitMessage(commitMessage) {
    return regex.reduce((acc, { regex, emoji }) => {
        return acc.replace(regex, emoji)
    }, commitMessage)
}

// Allow this to be run as a script from the command line
if (require.main === module) {
    const args = process.argv.slice(2)
    const commitMessage = args[0]
    console.log(emojifyCommitMessage(commitMessage))
}