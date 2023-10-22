/**
 * underscroreSpace - Replaces underscores with spaces
 *
 * @param value - The string to replace underscores with spaces
 * @returns The string with underscores replaced with spaces
 */
function underscroreSpaces(value: string): string {
    return value.replace(/_/g, ' ');
}

export default underscroreSpaces;
