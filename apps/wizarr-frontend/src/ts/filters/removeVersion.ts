/**
 * removeVersion - Removes the version numbers from a string
 *
 * @param value - The string to remove the version numbers from
 * @returns The string with the version numbers removed
 */
function removeVersion(value: string): string {
    return value.replace(/ \d+(\.\d+)*\s*/g, '');
}

export default removeVersion;
