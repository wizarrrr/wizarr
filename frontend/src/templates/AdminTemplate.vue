<template>
    <!-- Wrapper -->
    <div class="flex flex-col items-center justify-center md:pt-8">
        <!-- Border Box -->
        <div class="w-full rounded bg-none md:border dark:border-gray-700 light:border-gray-200" :class="class">
            <!-- Padded Area -->
            <div class="md:p-8 animate__animated animate__fadeIn">
                <!-- Header -->
                <div class="space-y-3 md:space-y-4 md:pb-6">
                    <div v-if="header || subheader || headerSlotAvailable" class="flex items-center justify-between border-b p-4 border-gray-200 dark:border-gray-600 md:p-0 md:border-none">
                        <div class="flex items-center">
                            <div class="flex flex-col justify-start">
                                <div class="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
                                    <Transition name="fade-fast" mode="out-in" :duration="{ enter: 300, leave: 300 }" v-if="transition">
                                        <span :key="header">
                                            {{ header ?? "" }}
                                        </span>
                                    </Transition>
                                    <span v-else>
                                        {{ header ?? "" }}
                                    </span>
                                </div>
                                <div class="text-sm font-semibold leading-tight tracking-tight text-gray-900 md:text-md dark:text-gray-400">
                                    <Transition name="fade-fast" mode="out-in" :duration="{ enter: 300, leave: 300 }" v-if="transition">
                                        <span :key="subheader">
                                            {{ subheader ?? "" }}
                                        </span>
                                    </Transition>
                                    <span v-else>
                                        {{ subheader ?? "" }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center justify-end space-x-2">
                            <slot name="header" />
                        </div>
                    </div>
                    <hr v-if="header || subheader || headerSlotAvailable" class="border-gray-200 dark:border-gray-700 hidden md:block" />
                </div>

                <!-- Content -->
                <div class="p-6 md:p-0">
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
        transition: {
            type: Boolean,
            default: false,
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
