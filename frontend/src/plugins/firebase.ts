import firebaseApp from "@/ts/utils/firebase";

import { getMessaging } from "firebase/messaging";

import type { App } from "vue";
import type { Messaging } from "firebase/messaging";

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        $firebase: typeof firebaseApp;
        $firebaseMessaging: Messaging;
    }
}

const vuePluginFirebase = {
    install: (app: App) => {
        app.config.globalProperties.$firebase = firebaseApp;
        app.config.globalProperties.$firebaseMessaging = getMessaging(firebaseApp);
    },
};

export default vuePluginFirebase;
