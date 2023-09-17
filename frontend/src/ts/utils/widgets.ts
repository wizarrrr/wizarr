import { defineAsyncComponent, type AsyncComponentLoader } from "vue";

import ErrorWidget from "@/widgets/ErrorWidget.vue";
import LoadingWidget from "@/widgets/LoadingWidget.vue";

export const getWidget = <T = string>(type: T): AsyncComponentLoader => {
    return defineAsyncComponent({
        loader: () => import(`../../widgets/${type}.vue`).then((m) => m.default).catch(() => import("@/widgets/ErrorWidget.vue")),
        errorComponent: ErrorWidget,
        loadingComponent: LoadingWidget,
    });
};
