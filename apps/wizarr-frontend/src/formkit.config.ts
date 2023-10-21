import { createProPlugin, inputs } from '@formkit/pro';

import ButtonInput from './components/FormKit/ButtonInput.vue';
import type { DefaultConfigOptions } from '@formkit/vue';
import OneTimePassword from './components/FormKit/OneTimePassword.vue';
import { createInput } from '@formkit/vue';
import formkitTheme from './formkit.theme';
import { generateClasses } from '@formkit/themes';
import { genesisIcons } from '@formkit/icons';

const iconLoader = (icon: string) => {
    const parent = document.createElement('div');
    parent.classList.add(
        'absolute',
        'inset-y-0',
        'left-0',
        'flex',
        'items-center',
        'pl-3.5',
        'pointer-events-none',
    );
    const i = document.createElement('i');
    i.classList.add('fas');
    icon.split(' ').forEach((c) => i.classList.add(c));
    parent.appendChild(i);
    return parent.innerHTML;
};

const proPlugin = createProPlugin('fk-80a76bd3e4', {
    ...inputs,
});

const config: DefaultConfigOptions = {
    icons: {
        ...genesisIcons,
    },
    iconLoader,
    // @ts-ignore
    plugins: [proPlugin],
    config: {
        classes: generateClasses(formkitTheme),
    },
    inputs: {
        otp: createInput(OneTimePassword, {
            props: ['digits'],
        }),
        inputButton: createInput(ButtonInput, {
            type: 'input',
        }),
    },
};

export default config;
