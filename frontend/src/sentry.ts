import * as Sentry from "@sentry/vue";
import { useServerStore } from "./stores/server";
import type { App } from "vue";
import type { Router } from "vue-router";

const init = (app: App<Element>, router: Router) => {
    // Get the server store for debug statement
    const serverStore = useServerStore();

    // Initialize Sentry
    Sentry.init({
        app,
        dsn: "https://d1994be8f88578e14f1a4ac06ae65e89@o4505748808400896.ingest.sentry.io/4505780347666432",
        integrations: [
            new Sentry.BrowserTracing({
                tracePropagationTargets: [location.origin],
                routingInstrumentation: Sentry.vueRouterInstrumentation(router),
            }),
            new Sentry.Replay({
                maskAllText: false,
                blockAllMedia: false,
                maskAllInputs: false,
            }),
        ],
        environment: process.env.NODE_ENV,
        tracesSampleRate: 1.0,
        replaysSessionSampleRate: 1.0,
        replaysOnErrorSampleRate: 1.0,
    });
};

console.log(process.env.NODE_ENV);

export default init;
