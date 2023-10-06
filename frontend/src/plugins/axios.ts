import mainAxios from "axios";

import type { App } from "vue";
import type { CreateAxiosDefaults } from "axios";
import type { PiniaPluginContext } from "pinia";

import { AxiosInterceptor, type CustomAxiosInstance } from "../ts/utils/axios";

declare module "pinia" {
    export interface PiniaCustomProperties {
        $axios: CustomAxiosInstance;
    }
}

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        $axios: CustomAxiosInstance;
    }
}

const useAxios = (options?: CreateAxiosDefaults) => {
    // Create a new axios instances
    const axiosDefault = mainAxios.create(options);
    const axios = new AxiosInterceptor(axiosDefault);

    // Return the axios instance
    return axios.axios;
};

const piniaPluginAxios = (context: PiniaPluginContext) => {
    // Create a new axios instances
    const axios = useAxios(context.options as CreateAxiosDefaults);

    // Add the axios instance to pinia
    context.store.$axios = axios;
};

const vuePluginAxios = {
    install: (app: App, options?: CreateAxiosDefaults) => {
        // Create a new axios instances
        const axios = useAxios(options);

        // Add the axios instance to the app
        app.config.globalProperties.$axios = axios;
    },
};

export default vuePluginAxios;
export { useAxios, piniaPluginAxios, vuePluginAxios };
