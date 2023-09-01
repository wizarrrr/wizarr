import type { AxiosInstance } from "axios";
import type { Toast } from "@/plugins/toasts";
import type { CustomAxiosInstance } from "@/assets/ts/utils/Axios";

declare module "*.vue" {
    import type { DefineComponent } from "vue";
    const component: DefineComponent<{}, {}, any>;
    export default component;
}

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        $axios: CustomAxiosInstance;
        $toast: Toast;
        $Progress: any;
    }
}

declare module "LINGUAS" {
    const LINGUAS: string;
    export default LINGUAS;
}
