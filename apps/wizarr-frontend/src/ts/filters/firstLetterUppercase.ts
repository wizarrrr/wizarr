/**
 * firstLetterUppercase - Capitalize the first letter of a string
 *
 * @param value - The string to capitalize the first letter of
 * @returns The string with the first letter capitalized
 */
function firstLetterUppercase(value: string): string {
    return value.charAt(0).toUpperCase() + value.slice(1);
}

export default firstLetterUppercase;
