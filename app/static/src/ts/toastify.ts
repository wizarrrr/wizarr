import Toastify from 'toastify-js';


// CREATE A CUSTOM TOASTIFY FUNCTION
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
        backgroundColor: '#fe4155',
        text: message,
    }).showToast();
}

const errorToast = (message: string) => {
    Toastify({
        text: message,
        backgroundColor: '#dc3545',
        ...defaultToast,
    }).showToast();
}

const successToast = (message: string) => {
    Toastify({
        text: message,
        backgroundColor: '#28a745',
        ...defaultToast,
    }).showToast();
}

const infoToast = (message: string) => {
    Toastify({
        text: message,
        backgroundColor: '#4B5563',
        ...defaultToast,
    }).showToast();
}

const warningToast = (message: string) => {
    Toastify({
        text: message,
        backgroundColor: '#ffc107',
        ...defaultToast,
    }).showToast();
}

// ADD FUNCTIONS TO THE WINDOW OBJECT
(window as any).toast = {};
(window as any).toast.showToast = showToast;
(window as any).toast.errorToast = errorToast;
(window as any).toast.infoToast = infoToast;
(window as any).toast.successToast = successToast;
(window as any).toast.warningToast = warningToast;
