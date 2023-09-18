import mitt, { type Emitter, type EventType } from "mitt";
import type { App, Component, VNodeProps } from "vue";
import { Transition, createVNode, defineComponent, render } from "vue";

declare module "@vue/runtime-core" {
    interface ComponentCustomProperties {
        $modal: {
            eventBus: Emitter<Record<EventType, any>>;
            create: (modal: Partial<ModalOptions>) => void;
            destroy: () => void;
            confirm: (title?: string, message?: string) => Promise<boolean>;
            [key: string]: any;
        };
    }
}

export type ModalOptions = {
    modal: {
        title?: string | Component;
        body?: string | Component;
        footer?: string | Component;
        buttons?: Array<Partial<HTMLButtonElement & { text: string; onClick: () => void }>>;
    };
    options: {
        showCloseButton?: boolean;
        showHeader?: boolean;
        showBody?: boolean;
        showFooter?: boolean;
        showOverlay?: boolean;
        hideOnOverlayClick?: boolean;
        hideOnEscapeKey?: boolean;
        closeButtonText?: string;
        disableAnimation?: boolean;
    };
    isVisible?: boolean;
};

const defaultModalOptions: ModalOptions["options"] = {
    showCloseButton: true,
    showHeader: true,
    showBody: true,
    showFooter: true,
    showOverlay: true,
    hideOnOverlayClick: false,
    hideOnEscapeKey: false,
    closeButtonText: "Cancel",
    disableAnimation: false,
};

const DefaultModal = defineComponent({
    name: "DefaultModal",
    data() {
        return {
            isVisible: false,
            modal: {},
            options: defaultModalOptions,
        } as ModalOptions;
    },
    methods: {
        onDestroy() {
            this.modal = {};
            this.options = defaultModalOptions;
            this.isVisible = false;
        },
        updateModal(modal: Partial<ModalOptions>) {
            this.modal = { ...this.modal, ...modal.modal };
            this.options = { ...this.options, ...modal.options };
            this.isVisible = true;
        },
    },
    mounted() {
        addEventListener("keydown", (e: KeyboardEvent) => {
            if (this.options.hideOnEscapeKey && e.key === "Escape") {
                this.isVisible = false;
            }
        });

        this.$modal.eventBus.on("create-modal", (modal: Partial<ModalOptions>) => {
            this.updateModal(modal);
        });

        this.$modal.eventBus.on("destroy-modal", () => {
            this.onDestroy();
        });
    },
    render() {
        return (
            <Transition name={this.options.disableAnimation ? "" : "fade"} onAfterLeave={() => this.onDestroy()} mode="out-in">
                {this.isVisible ? (
                    <div class="fixed top-0 bottom-0 left-0 right-0 flex z-30 items-center justify-center">
                        {this.options.showOverlay ? <div onClick={() => (this.isVisible = !this.options.hideOnOverlayClick)} class="fixed inset-0 bg-gray-700 bg-opacity-75 transition-opacity"></div> : null}
                        <div class="min-w-[800px] flex flex-col fixed top-0 bottom-0 left-0 right-0 h-full w-full md:h-auto md:w-auto transform text-left shadow-xl transition-all md:relative md:min-w-[30%] md:max-w-2xl md:shadow-none md:transform-none sm:align-middle text-gray-900 dark:text-white">
                            {/* Modal Title */}
                            <div class="flex items-center bg-white pl-6 p-3 dark:bg-gray-800 justify-between p-4 border-b dark:border-gray-600 rounded-t">
                                {this.modal?.title && typeof this.modal.title === "object" ? createVNode(this.modal.title) : null}
                                <h3 class="text-xl align-center font-semibold text-gray-900 dark:text-white">{this.modal?.title && typeof this.modal.title === "string" ? this.modal.title : null}</h3>
                                <button onClick={() => (this.isVisible = false)} type="button" class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm w-8 h-8 ml-auto inline-flex justify-center items-center dark:hover:bg-gray-600 dark:hover:text-white">
                                    <i class="fa-solid fa-times text-xl"></i>
                                </button>
                            </div>

                            {/* Modal Body */}
                            <div class="bg-white p-6 dark:bg-gray-800 p-6 space-y-6 flex-grow">
                                {this.modal?.body && typeof this.modal.body === "object" ? createVNode(this.modal.body) : null}
                                {this.modal?.body && typeof this.modal.body === "string" ? <p>{this.modal.body}</p> : null}
                            </div>

                            {/* Modal Footer */}
                            {this.options.showFooter ? (
                                <div class="flex items-center justify-end bg-white p-6 dark:bg-gray-800 p-6 space-x-2 border-t border-gray-200 dark:border-gray-600 rounded-b">
                                    {this.modal?.buttons?.map((button) => (
                                        // @ts-ignore
                                        <button onClick={button.onClick} {...button} type="button" class="px-5 py-2.5 text-sm whitespace-nowrap overflow-hidden overflow-ellipsis flex items-center justify-center relative bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded dark:bg-secondary dark:hover:bg-secondary_hover" key={button.text}>
                                            <span>{button.text}</span>
                                        </button>
                                    ))}
                                    {this.modal?.footer && typeof this.modal.footer === "object" ? createVNode(this.modal.footer) : null}
                                    {this.modal?.footer && typeof this.modal.footer === "string" ? <p>{this.modal.footer}</p> : null}
                                    {this.options.showCloseButton ? (
                                        <button onClick={() => (this.isVisible = false)} type="button" class="px-5 py-2.5 text-sm whitespace-nowrap overflow-hidden overflow-ellipsis flex items-center justify-center relative bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded dark:bg-secondary dark:hover:bg-secondary_hover">
                                            <span>{this.options.closeButtonText}</span>
                                        </button>
                                    ) : null}
                                </div>
                            ) : null}
                        </div>
                    </div>
                ) : null}
            </Transition>
        );
    },
});

const create = (eventBus: Emitter<Record<EventType, any>>, modal: Partial<ModalOptions>) => eventBus.emit("create-modal", modal) as unknown as void;
const destroy = (eventBus: Emitter<Record<EventType, any>>) => eventBus.emit("destroy-modal") as unknown as void;
const confirm = async (eventBus: Emitter<Record<EventType, any>>, title?: string, message?: string): Promise<boolean> => {
    return new Promise((resolve) => {
        eventBus.emit("create-modal", {
            options: {
                showCloseButton: false,
            },
            modal: {
                title: title ?? "Are you sure?",
                body: message ?? "Are you sure you want to continue?",
                buttons: [
                    {
                        class: "!bg-primary",
                        text: "Confirm",
                        onClick: () => {
                            eventBus.emit("destroy-modal");
                            resolve(true);
                        },
                    },
                    {
                        text: "Cancel",
                        onClick: () => {
                            eventBus.emit("destroy-modal");
                            resolve(false);
                        },
                    },
                ],
            },
        });
    });
};

/**
 * Vue Plugin
 *
 * This plugin will add a $modal function to the vue instance
 * allowing you to create modals from anywhere in your app
 */
const vuePluginModal = {
    install(vue: App) {
        const eventBus = mitt();
        vue.component("ModalContainer", DefaultModal);
        vue.config.globalProperties.$modal = {
            eventBus: eventBus,
            create: (modal: Partial<ModalOptions>) => create(eventBus, modal),
            destroy: () => destroy(eventBus),
            confirm: (title?: string, message?: string) => confirm(eventBus, title, message),
        };
    },
};

export default vuePluginModal;
