import { formatTimeAgo } from '@vueuse/core';
import moment from 'moment';

/**
 * timeAgo - Filter to convert a date to a time ago string (e.g. 5 minutes ago)
 *
 * @param {string} value - The date or date string to convert to a time ago string
 * @param {boolean} utc - Whether input date is in UTC
 * @returns The time ago string
 */
function timeAgo(value: string | Date, utc: boolean = true): string {
    const date = utc
        ? moment.utc(value).local().toDate()
        : moment(value).local().toDate();
    const now = utc ? moment.utc().local().toDate() : moment().local().toDate();
    return formatTimeAgo(date, { showSecond: true }, now);
}

export default timeAgo;
