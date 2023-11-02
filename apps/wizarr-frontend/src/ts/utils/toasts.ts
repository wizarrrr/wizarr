import { useToast } from 'vue-toastification';
import type {
    CommonOptions,
    PluginOptions,
    ToastContent,
    ToastID,
    ToastOptions,
} from 'vue-toastification/dist/types/types';

export const infoToast = (message: ToastContent, options?: ToastOptions) => {
    const toast = useToast();
    return toast.info(message, options as CommonOptions);
};

export const successToast = (message: ToastContent, options?: ToastOptions) => {
    const toast = useToast();
    return toast.success(message, options as CommonOptions);
};

export const errorToast = (message: ToastContent, options?: ToastOptions) => {
    const toast = useToast();
    return toast.error(message, options as CommonOptions);
};

export const warningToast = (message: ToastContent, options?: ToastOptions) => {
    const toast = useToast();
    return toast.warning(message, options as CommonOptions);
};

export const defaultToast = (message: ToastContent, options?: ToastOptions) => {
    const toast = useToast();
    toast(message, options as CommonOptions);
};

export const clearToasts = () => {
    const toast = useToast();
    toast.clear();
};

export const updateDefaultOptions = (options: PluginOptions) => {
    const toast = useToast();
    toast.updateDefaults(options);
};

export const dismissToast = (id: ToastID) => {
    const toast = useToast();
    toast.dismiss(id);
};

export const updateToast = (
    id: ToastID,
    content: ToastContent,
    options?: ToastOptions,
) => {
    const toast = useToast();
    toast.update(id, { content, options });
};

export default {
    info: infoToast,
    success: successToast,
    error: errorToast,
    warning: warningToast,
    default: defaultToast,
    clear: clearToasts,
    updateDefaults: updateDefaultOptions,
    dismiss: dismissToast,
    update: updateToast,
};

export declare type Toasts = {
    info: typeof infoToast;
    success: typeof successToast;
    error: typeof errorToast;
    warning: typeof warningToast;
    default: typeof defaultToast;
    clear: typeof clearToasts;
    updateDefaults: typeof updateDefaultOptions;
    dismiss: typeof dismissToast;
    update: typeof updateToast;
};
