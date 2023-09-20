import { Modal, closeById, closeModal, config, getComponentFromStore, getCurrentModal, modalQueue, onBeforeModalClose, openModal, popModal, promptModal, pushModal, useModalRouter } from "jenesius-vue-modal";

import type { App } from "vue";
import type { ConfigInterface } from "jenesius-vue-modal/dist/types/utils/config";
import type { FormKitClasses } from "@formkit/core";
import type { ModalOptions } from "jenesius-vue-modal/dist/types/utils/Modal";
import ModalWrapper from "./ModalWrapper";
import type { WrapComponent } from "jenesius-vue-modal/dist/types/types/types";

export declare interface CustomModalOptions extends Partial<ModalOptions> {
    title?: string;
    disableHeader?: boolean;
    disableCloseButton?: boolean;
    disableFooter?: boolean;
    enableConfirmButton?: boolean;
    confirmButtonText?: string;
    disableCancelButton?: boolean;
    cancelButtonText?: string;
    buttons?: Array<Partial<{ text: string; classes: Record<string, string | Record<string, boolean> | FormKitClasses>; onClick: () => void }>>;
}

const localOpenModal = async <P extends WrapComponent>(component: P | string, options?: Partial<CustomModalOptions>, props?: any): Promise<Modal> => {
    const componentWrapper = ModalWrapper(component, props, options);
    const newModal = await openModal(componentWrapper, props, options);
    newModal.on(Modal.EVENT_PROMPT, () => newModal.close());
    newModal.on("close", () => newModal.close());
    return newModal;
};

const confirmModal = async (title: string, message: string, options?: Partial<ModalOptions>): Promise<boolean> => {
    const componentWrapper = ModalWrapper(message, undefined, { title, enableConfirmButton: true });
    return (await promptModal(componentWrapper, { title, message }, options)) as boolean;
};

declare type CustomModal = {
    openModal: typeof localOpenModal;
    confirmModal: typeof confirmModal;
    closeModal: typeof closeModal;
    pushModal: typeof pushModal;
    popModal: typeof popModal;
    promptModal: typeof promptModal;
    modalQueue: typeof modalQueue;
    config: typeof config;
    onBeforeModalClose: typeof onBeforeModalClose;
    useModalRouter: typeof useModalRouter;
    getCurrentModal: typeof getCurrentModal;
    closeById: typeof closeById;
    getComponentFromStore: typeof getComponentFromStore;
};

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        $modal: CustomModal;
    }
}

const useModal = (): CustomModal => {
    return {
        openModal: localOpenModal,
        confirmModal,
        closeModal,
        pushModal,
        popModal,
        promptModal,
        modalQueue,
        config,
        onBeforeModalClose,
        useModalRouter,
        getCurrentModal,
        closeById,
        getComponentFromStore,
    };
};

const vuePluginModal = {
    install: (app: App, options?: Partial<ConfigInterface>) => {
        app.config.globalProperties.$modal = useModal();
        config(
            options ?? {
                scrollLock: true,
                animation: "fade",
                backgroundClose: false,
                escClose: true,
            },
        );
    },
};

export default vuePluginModal;
