const pickRandomEmoji = (...emojis) => {
    const randomIndex = Math.floor(Math.random() * emojis.length)
    return emojis[randomIndex]
}

const regex = [
    {
        regex: /(?<=^feat(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('✨', '🎉', '🎊', '🚀')
    },
    {
        regex: /(?<=^fix(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🐛', '🚑', '🩹', '🐝')
    },
    {
        regex: /(?<=^docs(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('📚', '📖', '📝')
    },
    {
        regex: /(?<=^style(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('💎', '🎨')
    },
    {
        regex: /(?<=^refactor(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('📦', '🔨', '🔧')
    },
    {
        regex: /(?<=^perf(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🚀', '🏎️', '🏍️', '🚄')
    },
    {
        regex: /(?<=^test(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🚨', '🚧', '🚥', '🔍')
    },
    {
        regex: /(?<=^build(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🏗️', '🧱', '🔨', '👷')
    },
    {
        regex: /(?<=^ci(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🤖', '🔧', '🧪')
    },
    {
        regex: /(?<=^chore(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🧹', '🧽', '🧼', '🧺')
    },
    {
        regex: /(?<=^revert(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🔙', '⏪', '🔁')
    },
    {
        regex: /(?<=^release(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🚀', '🎉', '🎊', '📦')
    },
    {
        regex: /(?<=^dependabot(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🤖', '🔧', '🧪')
    },
    {
        regex: /(?<=^first(\(.*\))?(:)?)\s/,
        emoji: pickRandomEmoji('🎉', '🎊', '🎈', '🎂')
    }
]

// Emojify a commit message
function emojifyCommitMessage(commitMessage) {
    return regex.reduce((acc, { regex, emoji }) => {
        return acc.replace(regex, ` ${emoji} `)
    }, commitMessage)
}

// Allow this to be run as a script from the command line
if (require.main === module) {
    // Get the commit message from the command line arguments
    const args = process.argv.slice(2)
    const commitMessage = args[0]

    // If the commit message already has an emoji, don't add another one
    if (commitMessage.match(/\p{Emoji_Presentation}/ug)) {
        console.log(commitMessage)
        return
    }

    console.log(emojifyCommitMessage(commitMessage))
}

// Command line usage:
// node emojify-commit-message.js "feat: add emojify-commit-message script"