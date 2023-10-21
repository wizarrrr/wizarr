/**
 * titleCase - Title cases a string with a minimum length attribute to ignore
 *
 * @param value - The string to title case
 * @returns The title cased string
 */
function titleCase(value: string): string {
    return value.replace(/\w\S*/g, (word: string) => {
        if (word.length > 3) {
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        } else {
            return word.toLowerCase();
        }
    });
}

export default titleCase;
