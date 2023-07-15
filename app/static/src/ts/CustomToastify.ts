import Toastify from 'toastify-js';


// CREATE A CUSTOM TOASTIFY OPTIONS
const defaultToast: Toastify.Options = {
    duration: 3000,
    gravity: 'bottom',
    position: 'right',
    className: 'toast',
    stopOnFocus: true
};

const showToast = (message: string, options: Toastify.Options) => {
    Toastify({
        ...defaultToast,
        ...options,
        style: {
            background: '#4B5563)',
        },
        text: message,
    }).showToast();
}

const errorToast = (message: string) => {
    Toastify({
        text: message,
        style: {
            background: '#dc3545',
        },
        ...defaultToast,
    }).showToast();
}

const successToast = (message: string) => {
    Toastify({
        text: message,
        style: {
            background: '#28a745',
        },
        ...defaultToast,
    }).showToast();
}

const infoToast = (message: string) => {
    Toastify({
        text: message,
        style: {
            background: '#4B5563',
        },
        ...defaultToast,
    }).showToast();
}

const warningToast = (message: string) => {
    Toastify({
        text: message,
        style: {
            background: '#ffc107',
        },
        ...defaultToast,
    }).showToast();
}

export default { name: "toast", errorToast, infoToast, showToast, successToast, warningToast };