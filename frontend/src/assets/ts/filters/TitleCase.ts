/*
 * TitleCase
 * Takes a string and uppercases the first letter of each word
 * unless the word is 3 or less letters long.
 *
 * @param {string} str
 * @returns {string}
 */
const TitleCase = (str: string) => {
    return str.replace(/\w\S*/g, (txt) => {
        if (txt.length > 3) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
        } else {
            return txt.toLowerCase();
        }
    });
};

export default TitleCase;
