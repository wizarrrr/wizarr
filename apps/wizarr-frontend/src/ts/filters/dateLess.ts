import moment from 'moment';

/**
 * dateLess - Filter that returns true if the first date is less than the second date
 *
 * @param {string} value - The first date to compare
 * @param {string} other - The second date to compare
 * @param {boolean} utc - Whether input date is in UTC
 * @returns The boolean result of the calculation
 */
function dateLess(
    value: string | Date,
    other: string | Date,
    utc: boolean = true,
): boolean {
    const date = utc ? moment.utc(value).local() : moment(value).local();
    const date2 = utc ? moment.utc(other).local() : moment(other).local();
    return date.isBefore(date2);
}

export default dateLess;
