import "./assets/scss/main.scss";

import Axios, { piniaPluginAxios } from "./plugins/axios";
import Filters, { piniaPluginFilters } from "./plugins/filters";
import Firebase, { piniaPluginFirebase } from "./plugins/firebase";
import Socket, { piniaPluginSocketIO } from "./plugins/socket";
import Toast, { piniaPluginToast } from "./plugins/toasts";
import Tours, { piniaPluginTours } from "./plugins/tours";
import WebShare, { piniaPluginWebShare } from "./plugins/webshare";
import { defaultConfig, plugin } from "@formkit/vue";

import Analytics from "./plugins/analytics";
import App from "./App.vue";
import FloatingVue from "floating-vue";
import Modal from "./plugins/modal";
import OpenLayersMap from "vue3-openlayers";
import ProgressOptions from "./assets/configs/DefaultProgress";
import Sentry from "./plugins/sentry";
import ToastOptions from "./assets/configs/DefaultToasts";
import ToastPlugin from "vue-toastification";
import VueFeather from "vue-feather";
import VueProgressBar from "@aacassandra/vue3-progressbar";
import { createApp } from "vue";
import { createPinia } from "pinia";
import formkitConfig from "./formkit.config";
import i18n from "./i18n";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import router from "./router";

import './md-editor'; // Initialize the markdown editor

const app = createApp(App);
const pinia = createPinia();

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        env: {
            NODE_ENV: "development" | "production";
        };
    }
}

app.config.globalProperties.env = {
    NODE_ENV: process.env.NODE_ENV as "development" | "production",
};

app.use(pinia);
app.use(router);
app.use(ToastPlugin, ToastOptions);
app.use(Axios);
app.use(Toast);
app.use(i18n);
app.use(VueProgressBar, ProgressOptions);
app.use(OpenLayersMap, { debug: true });
app.use(FloatingVue);
app.use(plugin, defaultConfig(formkitConfig));
app.use(Socket, { uri: window.location.origin });
app.use(Filters);
app.use(Sentry);
app.use(Analytics);
app.use(Modal);
app.use(WebShare);
app.use(Firebase);
app.use(Tours, { i18n: i18n });

app.component("VueFeather", VueFeather);

declare module "@vue/runtime-core" {
    interface GlobalComponents {
        VueFeather: typeof VueFeather;
    }
}

pinia.use(piniaPluginPersistedstate);
pinia.use(piniaPluginToast);
pinia.use(piniaPluginAxios);
pinia.use(piniaPluginSocketIO);
pinia.use(piniaPluginFilters);
pinia.use(piniaPluginWebShare);
pinia.use(piniaPluginFirebase);
pinia.use(piniaPluginTours);

app.mount("#app");

export { app, pinia };
