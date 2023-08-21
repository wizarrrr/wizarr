import addToWindow from './addToWindow';

// CREATE A CUSTOM TOASTIFY OPTIONS
const defaultToast: Toastify.Options = {
    duration: 3000,
    gravity: 'bottom',
    position: 'right',
    className: 'toast',
    stopOnFocus: true
};

const showToast = async (message: string, options: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        ...defaultToast,
        ...options,
        style: {
            background: '#4B5563)',
        },
        text: message,
    }).showToast();
}

const errorToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#dc3545',
        },
        ...defaultToast,
        ...options ?? {}
    }).showToast();
}

const successToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#28a745',
        },
        ...defaultToast,
        ...options ?? {}
    }).showToast();
}

const infoToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#4B5563',
        },
        ...defaultToast,
        ...options ?? {}
    }).showToast();
}

const warningToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#ffc107',
        },
        ...defaultToast,
        ...options ?? {}
    }).showToast();
}

addToWindow(["toast"], {
    errorToast,
    infoToast,
    showToast,
    successToast,
    warningToast,
});


export { errorToast, infoToast, showToast, successToast, warningToast };
