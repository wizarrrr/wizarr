import "./assets/scss/main.scss";
import "./assets/ts/index";

import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import ToastPlugin from "vue-toastification";
import ToastOptions from "./assets/configs/DefaultToasts";
import i18n from "./i18n";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import sentry from "./sentry";
import VueProgressBar from "@aacassandra/vue3-progressbar";
import FloatingVue from "floating-vue";
import router from "./router";

import Toast, { piniaPluginToast } from "./plugins/toasts";
import Axios, { piniaPluginAxios } from "./plugins/axios";

import formkitConfig from "./formkit.config";
import { plugin, defaultConfig } from "@formkit/vue";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.use(ToastPlugin, ToastOptions);
app.use(Axios);
app.use(Toast);
app.use(i18n);
app.use(VueProgressBar, {
    color: "rgb(254 65 85 / var(--tw-bg-opacity))",
    failedColor: "#f44336",
    thickness: "2px",
});

app.use(FloatingVue);
app.use(plugin, defaultConfig(formkitConfig));

pinia.use(piniaPluginPersistedstate);
pinia.use(piniaPluginToast);
pinia.use(piniaPluginAxios);

sentry(app, router);

app.mount("#app");

export { app, pinia };
