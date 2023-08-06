import axios from 'axios';

import addToWindow from '../utils/addToWindow';
import Authentication from '../utils/authentication';

const getMFA = async (id: number): Promise<any> => {
    const resp = await axios.get(`/api/mfa/${id}`);
    return resp.data;
}

const addMFA = async (name: string): Promise<void> => {
    // Initialize the authentication class
    const auth = new Authentication();

    // Start MFA registration
    await auth.mfaRegistration(name);
}

const editMFA = async (id: number): Promise<void> => {
    // Get the input element with the given id as data-id
    const input = document.querySelector(`input#mfa-input[data-id="${id}"]`) as HTMLInputElement;

    // Undisable the input and focus it
    input.disabled = false;
    input.focus();

    // Create a function to save the MFA
    const saveMFA = async (): Promise<void> => {
        await axios.put(`/api/mfa/${id}`, { name: input.value });
        input.disabled = true;
    }

    // Add an event listener to the input to listen for the enter key
    input.addEventListener('keydown', async (e: KeyboardEvent): Promise<void> => {
        if (e.key === 'Enter') {
            await saveMFA();
        }
    });

    // Add an event listener to the input to listen for the focusout event
    input.addEventListener('focusout', async (): Promise<void> => {
        await saveMFA();
    });
}

const deleteMFA = async (id: number): Promise<void> => {
    // Delete the MFA from the database
    await axios.delete(`/api/mfa/${id}`);

    // Get the div element with the given id as data-id
    const div = document.querySelector(`div#mfa-block[data-id="${id}"]`) as HTMLDivElement;

    // Remove the div from the DOM using animation
    div.classList.add('animate__animated', 'animate__fadeOut');

    // Wait for the animation to finish
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Remove the div from the DOM
    div.remove();

    // If parent has no children, unhide the mfa-block-empty div
    const parent = document.querySelector('div#mfa-blocks') as HTMLDivElement;
    if (parent.children.length === 0) {
        const empty = document.querySelector('div#mfa-block-empty') as HTMLDivElement;
        empty.classList.remove('d-none');
    }
}

addToWindow(['api', 'mfa', 'getMFA'], getMFA);
addToWindow(['api', 'mfa', 'addMFA'], addMFA);
addToWindow(['api', 'mfa', 'editMFA'], editMFA);
addToWindow(['api', 'mfa', 'deleteMFA'], deleteMFA);
