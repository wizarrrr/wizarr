import type { Toasts } from "@/assets/ts/utils/Toasts";
import toasts from "@/assets/ts/utils/Toasts";
import type { App } from "vue";

export declare type Toast = Toasts;

export default {
    install: (app: App) => {
        app.config.globalProperties.$toast = toasts;
    },
};
