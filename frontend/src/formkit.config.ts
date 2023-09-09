import { generateClasses } from "@formkit/themes";
import { genesisIcons } from "@formkit/icons";
import { createProPlugin, inputs } from "@formkit/pro";
import { createInput } from "@formkit/vue";

import type { DefaultConfigOptions } from "@formkit/vue";

import formkitTheme from "./formkit.theme";
import formkitLabel from "./plugins/formkitLabel";

import OneTimePassword from "./components/FormKit/OneTimePassword.vue";
import OptionalInput from "./components/FormKit/OptionalInput.vue";

const pro = createProPlugin("fk-80a76bd3e4", inputs);
const config: DefaultConfigOptions = {
    icons: {
        ...genesisIcons,
    },
    iconLoader(icon: string) {
        const parent = document.createElement("div");
        parent.classList.add("absolute", "inset-y-0", "left-0", "flex", "items-center", "pl-3.5", "pointer-events-none");
        const i = document.createElement("i");
        i.classList.add("fas", icon, "text-gray-400");
        parent.appendChild(i);
        return parent.innerHTML;
    },
    // @ts-ignore
    plugins: [pro, formkitLabel],
    config: {
        classes: generateClasses(formkitTheme),
    },
    inputs: {
        otp: createInput(OneTimePassword, {
            props: ["digits"],
        }),
        optionalInput: createInput(OptionalInput, {
            type: "input",
        }),
    },
};

export default config;
