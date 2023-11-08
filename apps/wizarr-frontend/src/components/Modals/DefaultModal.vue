<template>
    <Transition name="fade">
        <div class="relative z-30" v-if="visible">
            <div class="fixed inset-0 bg-gray-700 bg-opacity-75 transition-opacity"></div>
            <div class="fixed inset-0 z-10 md:overflow-y-auto">
                <div class="flex min-h-full items-center justify-center p-4 text-center sm:items-center sm:p-0">
                    <div class="flex flex-col fixed top-0 bottom-0 left-0 right-0 h-full w-full md:h-auto md:w-auto transform text-left shadow-xl transition-all md:relative md:min-w-[30%] md:max-w-2xl md:shadow-none md:transform-none sm:align-middle text-gray-900 dark:text-white" :class="modalClass">
                        <!-- Modal header -->
                        <div v-if="titleSlotAvailable" class="flex items-center bg-white pl-6 p-3 dark:bg-gray-800 justify-between p-4 border-b dark:border-gray-600">
                            <slot name="title"></slot>
                        </div>
                        <div v-else-if="title" class="flex items-center bg-white pl-6 p-3 dark:bg-gray-800 justify-between p-4 border-b dark:border-gray-600">
                            <component :is="title"></component>
                        </div>
                        <div v-else-if="titleString" class="flex items-center bg-white pl-6 p-3 dark:bg-gray-800 justify-between p-4 border-b dark:border-gray-600 rounded-t">
                            <h3 class="text-xl align-center font-semibold text-gray-900 dark:text-white">
                                {{ titleString }}
                            </h3>
                            <button type="button" @click="close()" class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm w-8 h-8 ml-auto inline-flex justify-center items-center dark:hover:bg-gray-600 dark:hover:text-white">
                                <i class="fa-solid fa-times text-xl"></i>
                            </button>
                        </div>

                        <!-- Modal body -->
                        <div
                            v-if="bodySlotAvailable || defaultSlotAvailable"
                            class="bg-white p-6 dark:bg-gray-800 p-6 space-y-6 flex-grow"
                            :class="{
                                'rounded-b': !footerSlotAvailable && !footer,
                                'rounded-t': !titleSlotAvailable && !title && !titleString,
                            }">
                            <slot v-if="bodySlotAvailable" name="body"></slot>
                            <slot v-else-if="defaultSlotAvailable" name="default"></slot>
                        </div>
                        <div v-else-if="body" class="bg-white p-6 dark:bg-gray-800 p-6 space-y-6 flex-grow">
                            <component :is="body"></component>
                        </div>

                        <!-- Modal footer -->
                        <div v-if="footerSlotAvailable" class="flex items-center justify-end bg-white p-6 dark:bg-gray-800 p-6 space-x-2 border-t border-gray-200 dark:border-gray-600 rounded-b">
                            <slot name="footer"></slot>
                            <DefaultButton @click="close()" v-if="showCloseButton">
                                {{ closeButtonText }}
                            </DefaultButton>
                        </div>
                        <div v-else-if="footer" class="flex items-center justify-end bg-white p-6 dark:bg-gray-800 p-6 space-x-2 border-t border-gray-200 dark:border-gray-600 rounded-b">
                            <component :is="footer"></component>
                            <DefaultButton @click="close()" v-if="showCloseButton">
                                {{ closeButtonText }}
                            </DefaultButton>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script lang="ts">
import { defineComponent } from "vue";

const mount = (component: any, options: any) => {
    const el = document.createElement("div");
    const vNode = component(options);
    const destroy = () => {
        vNode.component.proxy.$destroy();
        vNode.el.remove();
    };
    return { vNode, destroy, el };
};

import DefaultButton from "../Buttons/DefaultButton.vue";

const DefaultModal = defineComponent({
    name: "Modal",
    components: {
        DefaultButton,
    },
    props: {
        visible: {
            type: Boolean,
            default: false,
        },
        titleString: {
            type: String,
            default: null,
        },
        title: {
            type: Object,
        },
        body: {
            type: Object,
        },
        footer: {
            type: Object,
        },
        destroy: {
            type: Function,
            default: () => {},
        },
        showCloseButton: {
            type: Boolean,
            default: true,
        },
        closeButtonText: {
            type: String,
            default: "Cancel",
        },
        modalClass: {
            type: String,
            default: "",
        },
    },
    computed: {
        titleSlotAvailable() {
            return !!this.$slots.title;
        },
        bodySlotAvailable() {
            return !!this.$slots.body;
        },
        footerSlotAvailable() {
            return !!this.$slots.footer;
        },
        defaultSlotAvailable() {
            return !!this.$slots.default;
        },
    },
    methods: {
        close() {
            this.destroy();
            this.$emit("close");
        },
    },
});

const createModal = (title?: unknown, body?: unknown, footer?: unknown, props?: Partial<typeof DefaultModal.__defaults>) => {
    const { vNode, destroy, el } = mount(DefaultModal, {
        props: {
            titleString: typeof title === "string" && title ? title : null,
            destroy: () => destroy(),
            ...(props || {}),
        },
        children: {
            title: typeof title === "object" && title ? title : null,
            body: body,
            footer: footer,
        },
    });

    const open = () => {
        document.body.appendChild(el);
    };

    const close = () => {
        destroy();
    };

    return { vNode, destroy, el, open, close };
};

export default DefaultModal;
export { createModal };
</script>
