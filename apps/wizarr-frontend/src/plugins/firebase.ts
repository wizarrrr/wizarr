import type { App } from "vue";
import firebaseApp from "@/ts/utils/firebase";
import defaultValues from "@/assets/configs/DefaultValues";
import { getRemoteConfig, getValue, type RemoteConfig, fetchAndActivate } from "firebase/remote-config";
import type { PiniaPluginContext } from "pinia";

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        $firebase: typeof firebaseApp;
        $remoteConfig: RemoteConfig;
        $config: (key: string) => string;
    }
}

declare module "pinia" {
    export interface PiniaCustomProperties {
        $firebase: typeof firebaseApp;
        $remoteConfig: RemoteConfig;
        $config: (key: string) => string;
    }
}

const piniaPluginFirebase = (context: PiniaPluginContext) => {
    context.store.$firebase = context.app.config.globalProperties.$firebase;
    context.store.$remoteConfig = context.app.config.globalProperties.$remoteConfig;
    context.store.$config = context.app.config.globalProperties.$config;
};

const vuePluginFirebase = {
    install: (app: App) => {
        // Set the firebase app and remote config
        app.config.globalProperties.$firebase = firebaseApp;
        app.config.globalProperties.$remoteConfig = getRemoteConfig(firebaseApp);

        // Set the firebase remote config settings
        app.config.globalProperties.$remoteConfig.settings.minimumFetchIntervalMillis = 10800000; // 3 hours

        // Set the firebase remote config default values
        app.config.globalProperties.$remoteConfig.defaultConfig = defaultValues;

        // Fetch the firebase remote config
        fetchAndActivate(app.config.globalProperties.$remoteConfig).then((activated) => {
            console.log("\x1b[34m%s\x1b[0m", "[Firebase] " + (activated ? "\x1b[32m%s\x1b[0m" : "\x1b[33m%s\x1b[0m"), "Remote config " + (activated ? "fetched and activated" : "already fetched and activated"));
        });

        // Global function to retrieve a remote config value as a string
        app.config.globalProperties.$config = (key: string): string => getValue(app.config.globalProperties.$remoteConfig, key).asString();
    },
};

export default vuePluginFirebase;
export { piniaPluginFirebase, vuePluginFirebase };
