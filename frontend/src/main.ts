import "./assets/scss/main.scss";

import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import ToastPlugin from "vue-toastification";
import ToastOptions from "./assets/configs/DefaultToasts";
import i18n from "./i18n";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import VueProgressBar from "@aacassandra/vue3-progressbar";
import FloatingVue from "floating-vue";
import router from "./router";
import Sentry from "./plugins/sentry";

import Toast, { piniaPluginToast } from "./plugins/toasts";
import Axios, { piniaPluginAxios } from "./plugins/axios";
import Socket, { piniaPluginSocketIO } from "./plugins/socket";
import Filters, { piniaPluginFilters } from "./plugins/filters";

import formkitConfig from "./formkit.config";
import { plugin, defaultConfig } from "@formkit/vue";
// import { Plugin as VanillaPlugin } from "@flavorly/vanilla-components";

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
// app.use(VanillaPlugin);
app.use(FloatingVue);
app.use(plugin, defaultConfig(formkitConfig));
app.use(Socket, { uri: window.location.origin });
app.use(Filters);
app.use(Sentry);

pinia.use(piniaPluginPersistedstate);
pinia.use(piniaPluginToast);
pinia.use(piniaPluginAxios);
pinia.use(piniaPluginSocketIO);
pinia.use(piniaPluginFilters);

app.mount("#app");

export { app, pinia };
