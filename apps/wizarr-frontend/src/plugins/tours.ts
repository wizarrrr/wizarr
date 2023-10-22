import type { App } from 'vue';
import type { Language } from 'vue3-gettext';
import type { PiniaPluginContext } from 'pinia';
import type TourGuideOptions from '@sjmc11/tourguidejs/src/core/options';
import loadRouterTour from '@/tours';
import { useUserStore } from '@/stores/user';

export interface CustomTourGuideOptions extends TourGuideOptions {
    i18n?: Language;
    userStore?: ReturnType<typeof useUserStore>;
    app: App;
}

declare module 'pinia' {
    export interface PiniaCustomProperties {
        $tours: any;
    }
}

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $tours: any;
    }
}

const piniaPluginTours = (context: PiniaPluginContext) => {
    // Add the toast instance to pinia
    // context.store.$tours = getTour;
};

const vuePluginTours = {
    install: (app: App, options?: Partial<CustomTourGuideOptions>) => {
        loadRouterTour(app.config.globalProperties.$router, {
            ...options,
            app,
        });
    },
};

export default vuePluginTours;
export { piniaPluginTours, vuePluginTours };
