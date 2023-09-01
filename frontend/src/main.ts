import "./assets/scss/main.scss";
import "./assets/ts/index";

import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import Toast from "vue-toastification";
import Axios from "./plugins/axios";
import ToastPlugin from "./plugins/toasts";
import DefaultOptions from "./assets/configs/DefaultToasts";
import i18n from "./i18n";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import sentry from "./sentry";
import VueProgressBar from "@aacassandra/vue3-progressbar";
import FloatingVue from "floating-vue";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.use(Toast, DefaultOptions);
app.use(Axios);
app.use(ToastPlugin);
app.use(i18n);
app.use(VueProgressBar, {
    color: "rgb(254 65 85 / var(--tw-bg-opacity))",
    failedColor: "#f44336",
    thickness: "2px",
});

app.use(FloatingVue);

pinia.use(piniaPluginPersistedstate);
sentry(app, router);

app.mount("#app");

export { app, pinia };
