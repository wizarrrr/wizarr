import { generateClasses } from "@formkit/themes";
import { genesisIcons } from "@formkit/icons";
import { createProPlugin, inputs } from "@formkit/pro";
import { createInput } from "@formkit/vue";

import type { DefaultConfigOptions } from "@formkit/vue";

import formkitTheme from "./formkit.theme";
import OneTimePassword from "./components/FormKit/OneTimePassword.vue";

const iconLoader = (icon: string) => {
    const parent = document.createElement("div");
    parent.classList.add("absolute", "inset-y-0", "left-0", "flex", "items-center", "pl-3.5", "pointer-events-none");
    const i = document.createElement("i");
    i.classList.add("fas", icon, "text-gray-400");
    parent.appendChild(i);
    return parent.innerHTML;
};

const pro = createProPlugin("fk-80a76bd3e4", inputs);

const config: DefaultConfigOptions = {
    icons: {
        ...genesisIcons,
    },
    iconLoader,
    // @ts-ignore
    plugins: [pro],
    config: {
        classes: generateClasses(formkitTheme),
    },
    inputs: {
        otp: createInput(OneTimePassword, {
            props: ["digits"],
        }),
    },
};

export default config;
