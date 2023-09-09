import moment from "moment";

/**
 * toMinutes - Convert a string date or date object to minutes from now
 *
 * @param {string | Date} value - The date or date string to convert to minutes from now
 * @returns The minutes from now
 */
function toMinutes(value: string | Date): number {
    return moment(value).diff(moment(), "minutes");
}

export default toMinutes;
