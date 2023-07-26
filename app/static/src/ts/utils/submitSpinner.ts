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

addToWindow(['utils', 'submitSpinner'], submitSpinner);