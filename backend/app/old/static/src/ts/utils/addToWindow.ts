type AnyLengthArray<T> = Array<T>;

const addToWindow = (name: Array<string>, value: Function | object | Array<any>) => {

    // Get the length of the array
    const length = name.length;

    // If the length is 1, we can just add the value to the window
    if (length === 1) {
        if (typeof value === 'function') {
            window[name[0]] = value;
        } else if (typeof value === 'object') {
            window[name[0]] = { ...value };
        } else if (Array.isArray(value)) {
            window[name[0]] = [...value];
        } else {
            window[name[0]] = value;
        }
        return;
    }

    let current = window;

    for (let i = 0; i < length; i++) {
        if (!current[name[i]]) {
            current[name[i]] = {};
        }

        if (i === length - 1) {
            if (typeof value === 'function') {
                current[name[i]] = value;
            } else if (typeof value === 'object') {
                current[name[i]] = { ...value };
            } else if (Array.isArray(value)) {
                current[name[i]] = [...value];
            } else {
                current[name[i]] = value;
            }
        }

        current = current[name[i]];
    }
}

export default addToWindow;
