import { BrowserTracing, Replay, init, vueRouterInstrumentation } from "@sentry/vue";
import DefaultToast from "@/components/Toasts/DefaultToast.vue";

import type { Options, TracingOptions } from "@sentry/vue/types/types";
import type { App } from "vue";

type SentryOptions = Partial<
    Omit<Options, "tracingOptions"> & {
        tracingOptions: Partial<TracingOptions>;
    }
>;

const vuePluginSentry = {
    install: (app: App, options?: SentryOptions) => {
        init({
            dsn: "https://d1994be8f88578e14f1a4ac06ae65e89@o4505748808400896.ingest.sentry.io/4505780347666432",
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
            replaysSessionSampleRate: 1.0,
            replaysOnErrorSampleRate: 1.0,
            beforeSend(event, hint) {
                if (event.exception) {
                    const errorMessage = event.message ?? "Unknown error";
                    app.config.globalProperties.$toast.error(DefaultToast("Detected Error", `${errorMessage}, this can generally be ignored.`));
                }
                return event;
            },
            ...options,
        });
    },
};

export default vuePluginSentry;
