import toasts from '@/ts/utils/toasts';

import type { Toasts } from '@/ts/utils/toasts';
import type { PiniaPluginContext } from 'pinia';
import type { App } from 'vue';

declare module 'pinia' {
    export interface PiniaCustomProperties {
        $toast: Toasts;
    }
}

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $toast: Toasts;
    }
}

const useToast = () => {
    // Return the toast instance
    return toasts;
};

const piniaPluginToast = (context: PiniaPluginContext) => {
    // Add the toast instance to pinia
    context.store.$toast = toasts;
};

const vuePluginToast = {
    install: (app: App) => {
        // Add the toast instance to the app
        app.config.globalProperties.$toast = toasts;
    },
};

export default vuePluginToast;
export { useToast, piniaPluginToast, vuePluginToast };
