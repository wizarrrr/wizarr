import { defineAsyncComponent, type AsyncComponentLoader } from 'vue';

import ErrorWidget from '@/widgets/components/ErrorWidget.vue';
import LoadingWidget from '@/widgets/components/LoadingWidget.vue';

export const getWidget = <T = string>(type: T): AsyncComponentLoader => {
    return defineAsyncComponent({
        loader: () =>
            import(`../../widgets/default/${type}.vue`)
                .then((m) => m.default)
                .catch(() => import('@/widgets/components/ErrorWidget.vue')),
        errorComponent: ErrorWidget,
        loadingComponent: LoadingWidget,
    });
};
