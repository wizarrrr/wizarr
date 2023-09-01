import addToWindow from './addToWindow';

function debounce(func: any, wait: number, immediate: boolean) {
    let timeout: any;
    return function () {
        // @ts-ignore-next-line
        const context = this, args = arguments;
        const later = function () {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;

        clearTimeout(timeout);
        timeout = setTimeout(later, wait);

        if (callNow) func.apply(context, args);
    };
};

addToWindow(['utils', 'debounce'], debounce);
export default debounce;