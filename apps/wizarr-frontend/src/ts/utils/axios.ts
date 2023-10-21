import mainAxios, {
    Axios,
    type AxiosRequestConfig,
    type AxiosResponse,
    type InternalAxiosRequestConfig,
} from 'axios';
import cookie from 'js-cookie';
import Auth from '@/api/authentication';

import { errorToast, infoToast } from './toasts';
import { useAuthStore } from '@/stores/auth';
import { useToast } from '@/plugins/toasts';

export interface CustomAxiosResponse<D = any> extends AxiosResponse {
    config: CustomAxiosRequestConfig<D> & InternalAxiosRequestConfig;
}

export interface CustomAxiosRequestConfig<D = any>
    extends AxiosRequestConfig<D> {
    disableInfoToast?: boolean;
    disableErrorToast?: boolean;
    refresh_header?: boolean;
}

export interface CustomAxiosInstance extends Axios {
    disableInfoToast?: boolean;
    disableErrorToast?: boolean;
    refresh_header?: boolean;
    getUri(config?: CustomAxiosRequestConfig): string;
    request<T = any, R = CustomAxiosResponse<T>, D = any>(
        config: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    get<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    delete<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    head<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    options<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    post<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        data?: D,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    put<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        data?: D,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    patch<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        data?: D,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    postForm<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        data?: D,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    putForm<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        data?: D,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
    patchForm<T = any, R = CustomAxiosResponse<T>, D = any>(
        url: string,
        data?: D,
        config?: CustomAxiosRequestConfig<D>,
    ): Promise<R>;
}

class AxiosInterceptor {
    // Axios instance and progress store
    public axios: CustomAxiosInstance = mainAxios.create();

    /*
     * Constructor to apply interceptors
     */
    constructor(axios: CustomAxiosInstance) {
        // Apply interceptors
        axios.interceptors.response.use(
            this.resp.bind(this),
            this.error.bind(this),
        );
        axios.interceptors.request.use(
            this.req.bind(this),
            this.error.bind(this),
        );
        axios.defaults.headers.common['X-CSRF-TOKEN'] =
            cookie.get('csrf_access_token');

        // If localstorage has a base url, set it
        if (typeof window !== 'undefined') {
            if (localStorage.getItem('base_url')) {
                axios.defaults.baseURL = localStorage.getItem(
                    'base_url',
                ) as string;
            }
        }

        // Set axios instance
        this.axios = axios;
    }

    /*
     * Interceptor for axios request
     * @param config
     * @returns {any}
     */
    public req(config: InternalAxiosRequestConfig & CustomAxiosRequestConfig) {
        // Try to add the authorization header to the request
        try {
            const authStore = useAuthStore();

            if (
                config.refresh_header &&
                (authStore.refresh_token?.length ?? 0) > 0
            ) {
                config.headers[
                    'Authorization'
                ] = `Bearer ${authStore.refresh_token}`;
            }

            if (
                (authStore.token?.length ?? 0) > 0 &&
                !config.refresh_header &&
                (authStore.refresh_token?.length ?? 0) > 0
            ) {
                config.headers['Authorization'] = `Bearer ${authStore.token}`;
            }
        } catch (e) {
            // Do nothing
        }

        return config;
    }

    /*
     * Interceptor for axios response
     * @param resp
     * @returns {any}
     */
    public resp<V>(resp: CustomAxiosResponse) {
        // If response has a message, show it
        if (!this.axios.disableInfoToast && !resp.config.disableInfoToast) {
            if (resp.data?.message) {
                infoToast(resp.data.message);
            }
        }

        return resp;
    }

    /*
     * Interceptor for axios error
     * @param error
     * @returns {any}
     */
    public async error(error: any) {
        if (this.axios.disableErrorToast || error.config.disableErrorToast) {
            return Promise.reject(error);
        }

        const showErrorToast = (message: string) => errorToast(message);

        const { response } = error;
        if (response?.data) {
            const { errors, message } = response.data as {
                errors?: Record<string, string[] | string>;
                message?: string;
            };
            if (errors) {
                Object.values(errors).forEach(
                    (errorMessages: string[] | string) => {
                        if (Array.isArray(errorMessages)) {
                            errorMessages.forEach((errorMessage: string) => {
                                showErrorToast(errorMessage);
                            });
                        } else if (typeof errorMessages === 'string') {
                            showErrorToast(errorMessages);
                        }
                    },
                );
            } else if (message) {
                showErrorToast(message);
            }
        }

        if (response?.status === 401) {
            try {
                const auth = new Auth();
                auth.logout();
            } catch (e) {
                useToast().error(
                    'An unauthenticated request was made, but we failed to log you out. Please refresh the page.',
                );
            }
        }

        return Promise.reject(error);
    }
}

// Create a new instance of AxiosInterceptor
const axios = () => new AxiosInterceptor(mainAxios).axios;

export default axios;
export { AxiosInterceptor };
