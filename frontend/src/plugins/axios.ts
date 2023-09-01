import mainAxios from "axios";
import cookie from "js-cookie";

import type { App } from "vue";
import type { CreateAxiosDefaults } from "axios";

import { AxiosInterceptor } from "../assets/ts/utils/Axios";

export default {
    install: (app: App, options?: CreateAxiosDefaults) => {
        const axiosDefault = mainAxios.create(options);
        const axios = new AxiosInterceptor(axiosDefault);
        app.config.globalProperties.$axios = axios.axios;
    },
};
