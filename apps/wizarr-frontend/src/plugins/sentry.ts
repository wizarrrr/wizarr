import { BrowserTracing, Replay, init, vueRouterInstrumentation } from "@sentry/vue";
import type { Options, TracingOptions } from "@sentry/vue/types/types";

import type { App } from "vue";
import DefaultToast from "@/components/Toasts/DefaultToast.vue";

type SentryOptions = Partial<
    Omit<Options, "tracingOptions"> & {
        tracingOptions: Partial<TracingOptions>;
    }
>;

const vuePluginSentry = {
    install: (app: App, options?: SentryOptions) => {
        init({
            app: app,
            dsn: "https://4034e578d899247f5121cbae3466e637@sentry.wizarr.dev/2",
            integrations: [
                new BrowserTracing({
                    tracePropagationTargets: [location.origin],
                    routingInstrumentation: vueRouterInstrumentation(app.config.globalProperties.$router),
                }),
                new Replay({
                    maskAllText: false,
                    blockAllMedia: false,
                    maskAllInputs: false,
                }),
            ],
            environment: process.env.NODE_ENV,
            tracesSampleRate: 1.0,
            replaysSessionSampleRate: 0.1,
            replaysOnErrorSampleRate: 1.0,
            beforeSend(event, hint) {
                if (event.exception) {
                    console.error(event, hint);

                    const originalException = hint.originalException as Error;
                    const message = originalException?.message;

                    if (message) {
                        app.config.globalProperties.$toast.error(DefaultToast("Error Message", message));
                        app.config.globalProperties.$toast.warning(DefaultToast("We noticed an error", `Errors occur sometimes naturally, but if you encounter behavior that seems wrong, please report it to us.`));
                    }
                }
                return event;
            },
            ...options,
        });
    },
};

export default vuePluginSentry;
