<template>
    <button @click="buttonClick()" class="relative bg-white rounded shadow-md dark:bg-gray-800 dark:border dark:border-gray-700 overflow-hidden hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer group transition duration-150 ease-in-out" :class="{ 'opacity-50 cursor-not-allowed': disabled, classes: classes }" :disabled="disabled">
        <div class="flex flex-row justify-start p-3 items-center">
            <div class="aspect-square h-[40px] w-[40px] p-3 bg-gray-100 rounded flex items-center justify-center bg-gray-100 dark:bg-gray-700 group-hover:bg-gray-200 dark:group-hover:bg-gray-600 transition duration-150 ease-in-out">
                <i class="text-gray-400" :class="icon"></i>
            </div>
            <div class="flex flex-col ml-4">
                <div class="settings-item-title text-sm font-bold text-start leading-tight tracking-tight text-gray-900 md:text-md dark:text-gray-400 line-clamp-1">
                    {{ __(title) }}
                </div>
                <div class="settings-item-description text-xs text-start leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400 line-clamp-1">
                    {{ __(description) }}
                </div>
            </div>
        </div>
    </button>
</template>

<script lang="ts">
import { defineComponent, defineAsyncComponent } from "vue";

export default defineComponent({
    name: "SettingsButton",
    props: {
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: true,
        },
        icon: {
            type: String,
            required: true,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        classes: {
            type: String,
            default: "",
        },
        url: {
            type: String,
            default: "",
        },
        modal: {
            type: Boolean,
            default: false,
        },
    },
    methods: {
        buttonClick() {
            if (this.modal) {
                this.createModal();
            } else {
                this.$router.push(this.url);
            }
        },
        async createModal() {
            this.$router.getRoutes().forEach(async (route) => {
                if (route.path === this.url && route.components) {
                    this.$modal.openModal(defineAsyncComponent(route.components.default as any), {
                        title: this.title,
                        disableFooter: true,
                    });
                }
            });
        },
    },
});
</script>
