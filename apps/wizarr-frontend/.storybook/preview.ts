import "../src/assets/scss/main.scss";

import { defaultConfig, plugin } from "@formkit/vue";

import formkitConfig from "../src/formkit.config";
import { setup } from "@storybook/vue3";

setup((app) => {
    app.use(plugin, defaultConfig(formkitConfig));
});
