import moment from 'moment';

/**
 * toMinutes - Convert a string date or date object to minutes from now
 *
 * @param value - The date or date string to convert to minutes from now
 * @param utc - Whether to use UTC or not
 * @returns The minutes from now
 */
function toMinutes(value: string | Date, utc: boolean = true): number {
    // Define different moments for the local times
    const localDateTime = utc ? moment.utc(value) : moment(value);
    const localNow = moment();

    // Calculate the difference in minutes between the times
    return localDateTime.diff(localNow, 'minutes');
}

export default toMinutes;
