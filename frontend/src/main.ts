import "./assets/scss/main.scss";

import Axios, { piniaPluginAxios } from "./plugins/axios";
import Filters, { piniaPluginFilters } from "./plugins/filters";
import Socket, { piniaPluginSocketIO } from "./plugins/socket";
import Toast, { piniaPluginToast } from "./plugins/toasts";
import WebShare, { piniaPluginWebShare } from "./plugins/webshare";
import { defaultConfig, plugin } from "@formkit/vue";

import Analytics from "./plugins/analytics";
import App from "./App.vue";
import FloatingVue from "floating-vue";
import Modal from "./plugins/modal";
import OpenLayersMap from "vue3-openlayers";
import Sentry from "./plugins/sentry";
import ToastOptions from "./assets/configs/DefaultToasts";
import ToastPlugin from "vue-toastification";
import VueProgressBar from "@aacassandra/vue3-progressbar";
import { createApp } from "vue";
import { createPinia } from "pinia";
import formkitConfig from "./formkit.config";
import i18n from "./i18n";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import router from "./router";

// import Plugin from "@flavorly/vanilla-components";

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
// app.use(Plugin as any);
app.use(OpenLayersMap, { debug: true });
app.use(FloatingVue);
app.use(plugin, defaultConfig(formkitConfig));
app.use(Socket, { uri: window.location.origin });
app.use(Filters);
app.use(Sentry);
app.use(Analytics);
app.use(Modal);
app.use(WebShare);

pinia.use(piniaPluginPersistedstate);
pinia.use(piniaPluginToast);
pinia.use(piniaPluginAxios);
pinia.use(piniaPluginSocketIO);
pinia.use(piniaPluginFilters);
pinia.use(piniaPluginWebShare);

app.mount("#app");

export { app, pinia };
