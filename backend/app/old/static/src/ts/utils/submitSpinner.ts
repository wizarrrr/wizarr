import addToWindow from './addToWindow';

const submitSpinner = (form: HTMLFormElement, active: boolean) => {
    const submitButton = form.querySelector('button[type="submit"]') as HTMLButtonElement;

    if (!submitButton) {
        return;
    }

    if (active === false) {
        if (submitButton.dataset.originalContent) {
            submitButton.innerHTML = submitButton.dataset.originalContent ?? '';
        }
        submitButton.disabled = false;
        delete submitButton.dataset.originalContent;
        return;
    }

    if (!submitButton.dataset.originalContent) {
        submitButton.dataset.originalContent = submitButton.innerHTML;
    }

    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
}

const buttonSpinner = (button: HTMLButtonElement, active: boolean) => {
    if (!button) {
        return;
    }

    if (active === false) {
        if (button.dataset.originalContent) {
            button.innerHTML = button.dataset.originalContent ?? '';
        }
        button.style.width = '';
        button.disabled = false;
        delete button.dataset.originalContent;
        return;
    }

    if (!button.dataset.originalContent) {
        button.dataset.originalContent = button.innerHTML;
    }

    button.style.width = button.offsetWidth + 'px';
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
}

addToWindow(['utils', 'submitSpinner'], submitSpinner);
addToWindow(['utils', 'buttonSpinner'], buttonSpinner);

export { submitSpinner, buttonSpinner }