import { useToast } from "vue-toastification";
import type { CommonOptions, ToastContent, ToastID } from "vue-toastification/dist/types/types";

export const infoToast = (message: ToastContent, options?: CommonOptions) => {
    const toast = useToast();
    return toast.info(message, options);
};

export const successToast = (message: ToastContent, options?: CommonOptions) => {
    const toast = useToast();
    return toast.success(message, options);
};

export const errorToast = (message: ToastContent, options?: CommonOptions) => {
    const toast = useToast();
    return toast.error(message, options);
};

export const warningToast = (message: ToastContent, options?: CommonOptions) => {
    const toast = useToast();
    return toast.warning(message, options);
};

export const defaultToast = (message: ToastContent, options?: CommonOptions) => {
    const toast = useToast();
    toast(message, options);
};

export const clearToasts = () => {
    const toast = useToast();
    toast.clear();
};

export const updateDefaultOptions = (options: CommonOptions) => {
    const toast = useToast();
    toast.updateDefaults(options);
};

export const dismissToast = (id: ToastID) => {
    const toast = useToast();
    toast.dismiss(id);
};

export const updateToast = (id: ToastID, content: ToastContent, options?: CommonOptions) => {
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
