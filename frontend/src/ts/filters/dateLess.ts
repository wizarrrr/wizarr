import moment from "moment";

/**
 * dateLess - Filter that returns true if the first date is less than the second date
 *
 * @param {string} value - The first date to compare
 * @param {string} other - The second date to compare
 * @param {boolean} utc - Whether input date is in UTC
 * @returns The boolean result of the calculation
 */
function dateLess(value: string | Date, other: string | Date, utc: boolean = true): boolean {
    if (utc) {
        value = moment.utc(value).local();
        other = moment.utc(other).local();
    } else {
        value = moment(value).local();
        other = moment(other).local();
    }

    return value.isBefore(other);
}

export default dateLess;
