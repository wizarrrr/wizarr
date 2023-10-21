import type { AxiosInstance } from 'axios';
import type { Toasts } from '@/assets/ts/utils/Toasts';
import type { CustomAxiosInstance } from '@/assets/ts/utils/Axios';

declare module '*.vue' {
    import type { DefineComponent } from 'vue';
    const component: DefineComponent<{}, {}, any>;
    export default component;
}

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $axios: CustomAxiosInstance;
        $toast: Toasts;
        $Progress: any;
    }
}

declare module 'LINGUAS' {
    const LINGUAS: string;
    export default LINGUAS;
}
