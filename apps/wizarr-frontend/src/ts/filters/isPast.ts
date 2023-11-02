import moment from 'moment';

/**
 * isPast - Filter to determine if a date is in the past
 *
 * @param {string} value - The date or date string to calculate if it is in the past
 * @param {boolean} utc - Whether input date is in UTC
 * @returns The boolean result of the calculation
 */
function isPast(value: string | Date, utc: boolean = true): boolean {
    const date = utc ? moment.utc(value).local() : moment(value).local();
    const now = utc ? moment.utc().local() : moment();
    return date.isBefore(now);
}

export default isPast;
