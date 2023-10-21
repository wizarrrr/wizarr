import type { App } from 'vue';
import type { PiniaPluginContext } from 'pinia';

export interface WebShare {
    share: (
        data: ShareData,
        fallback?: () => Promise<void> | void,
    ) => Promise<void>;
    isSupported: boolean;
}

export interface WebShareOptions {
    fallback?: () => Promise<void> | void;
}

declare module 'pinia' {
    export interface PiniaCustomProperties {
        $share: typeof share;
    }
}

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $share: typeof share;
    }
}

const useWebShare = (options?: WebShareOptions) => {
    return {
        share: (data: ShareData, fallback?: () => Promise<void> | void) =>
            share(data, fallback ?? options?.fallback),
        isSupported: 'share' in navigator,
    } as WebShare;
};

const share = async (
    data: ShareData,
    fallback?: () => Promise<void> | void,
) => {
    try {
        await navigator.share(data);
    } catch {
        await fallback?.();
    }
};

const piniaPluginWebShare = (context: PiniaPluginContext) => {
    // Add the toast instance to pinia
    context.store.$share = context.app.config.globalProperties.$share;
};

const vuePluginWebShare = {
    install: (app: App) => {
        // Add the toast instance to the app
        app.config.globalProperties.$share = share;
    },
};

export default vuePluginWebShare;
export { useWebShare, piniaPluginWebShare, vuePluginWebShare };
