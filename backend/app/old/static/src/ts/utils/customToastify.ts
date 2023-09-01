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
    const toast = Toastify.default({
        ...defaultToast,
        ...options,
        style: {
            background: '#4B5563)',
        },
        text: message,
    })

    toast.showToast();
    return toast;
}

const errorToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    const toast = Toastify.default({
        text: message,
        style: {
            background: '#dc3545',
        },
        ...defaultToast,
        ...options ?? {}
    })

    toast.showToast();
    return toast;
}

const successToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    const toast = Toastify.default({
        text: message,
        style: {
            background: '#28a745',
        },
        ...defaultToast,
        ...options ?? {}
    })

    toast.showToast();
    return toast;
}

const infoToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    const toast = Toastify.default({
        text: message,
        style: {
            background: '#4B5563',
        },
        ...defaultToast,
        ...options ?? {}
    })

    toast.showToast();
    return toast;
}

const warningToast = async (message: string, options?: Toastify.Options) => {
    const Toastify = await import("toastify-js");
    const toast = Toastify.default({
        text: message,
        style: {
            background: '#ffc107',
        },
        ...defaultToast,
        ...options ?? {}
    })

    toast.showToast();
    return toast;
}

addToWindow(["toast"], {
    errorToast,
    infoToast,
    showToast,
    successToast,
    warningToast,
});


export { errorToast, infoToast, showToast, successToast, warningToast };
