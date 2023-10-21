import { AnalyticsBrowser } from '@segment/analytics-next';
import { nanoid } from 'nanoid';

import type {
    AnalyticsBrowserSettings,
    InitOptions,
} from '@segment/analytics-next';
import type { App } from 'vue';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $analytics: AnalyticsBrowser;
    }
}

const vuePluginAnalytics = {
    install: (
        app: App,
        options?: {
            settings?: AnalyticsBrowserSettings;
            options?: InitOptions;
        },
    ): void => {
        // Get base URL from localStorage or use window.location.origin
        const baseURL =
            localStorage.getItem('base_url') ?? window.location.origin;

        // Default settings
        const defaultSettings: AnalyticsBrowserSettings = {
            // cdnURL: baseURL,
            // cdnURL: "https://webhook.site/44c93238-6e85-4736-a1f4-90bb007afc0b",
            // writeKey: "wizarr",
            writeKey: 'rAjFFBAQf10L1mwRl4MlwDVYBYLcRdGY',
        };

        // Default options
        const defaultOptions: InitOptions = {};

        // Load analytics
        const analytics = AnalyticsBrowser.load(
            defaultSettings,
            defaultOptions,
        );

        // Intergate with Vue Router to track page views
        app.config.globalProperties.$router.beforeEach((to, from) => {
            analytics.page({
                path: to.path,
                referrer: from.path,
                url: `${baseURL}${to.path}`,
                title: to.name,
                search: to.query,
                id: nanoid(),
            });
        });

        // Set global properties
        app.config.globalProperties.$analytics = analytics;
    },
};

export default vuePluginAnalytics;
