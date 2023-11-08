<template>
    <!-- Wrapper -->
    <div class="absolute top-0 left-0 bottom-0 right-0 mt-[64px] mb-[33px]">
        <!-- Border Box -->
        <div class="w-full rounded bg-none dark:border-gray-700 light:border-gray-200" :class="class">
            <!-- Header -->
            <!-- max-w-screen-xl flex flex-col md:flex-row items-start md:items-center justify-between mx-auto p-4 -->
            <div v-if="header || subheader || headerSlotAvailable" class="flex items-center justify-center bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-600 h-[75px]">
                <div class="w-full max-w-screen-xl flex flex-row justify-between p-4">
                    <div class="flex items-center">
                        <div class="flex flex-col justify-start">
                            <div class="text-xl font-bold leading-tight tracking-tight text-gray-900 dark:text-white">
                                {{ header ?? "" }}
                            </div>
                            <div class="text-sm font-semibold leading-tight tracking-tight text-gray-900 dark:text-gray-400">
                                {{ subheader ?? "" }}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center justify-end space-x-2">
                        <slot name="header" />
                    </div>
                </div>
            </div>

            <!-- Content -->
            <div class="absolute top-0 left-0 bottom-0 right-0 mt-[75px]">
                <slot />
            </div>

            <!-- Footer -->
            <div v-if="footerSlotAvailable || footerActionsSlotAvailable" class="flex items-center justify-between mb-6 md:mb-0 px-6 md:px-0">
                <div class="flex items-center">
                    <slot name="footer" />
                </div>
                <div class="flex items-center justify-end space-x-2">
                    <slot name="footerActions" />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Box",
    props: {
        header: {
            type: String,
        },
        subheader: {
            type: String,
        },
        class: {
            type: String,
            default: "",
        },
    },
    computed: {
        headerSlotAvailable() {
            return this.$slots.header !== undefined;
        },
        footerSlotAvailable() {
            return this.$slots.footer !== undefined;
        },
        footerActionsSlotAvailable() {
            return this.$slots.footerActions !== undefined;
        },
    },
});
</script>
