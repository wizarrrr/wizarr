
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

const errorToast = async (message: string) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#dc3545',
        },
        ...defaultToast,
    }).showToast();
}

const successToast = async (message: string) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#28a745',
        },
        ...defaultToast,
    }).showToast();
}

const infoToast = async (message: string) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#4B5563',
        },
        ...defaultToast,
    }).showToast();
}

const warningToast = async (message: string) => {
    const Toastify = await import("toastify-js");
    Toastify.default({
        text: message,
        style: {
            background: '#ffc107',
        },
        ...defaultToast,
    }).showToast();
}

export default { name: "toast", errorToast, infoToast, showToast, successToast, warningToast };
export { errorToast, infoToast, showToast, successToast, warningToast };
