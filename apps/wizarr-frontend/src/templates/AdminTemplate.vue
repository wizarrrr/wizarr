<template>
    <!-- Page -->
    <div :class="boxPageClass">
        <!-- Wrapper -->
        <div class="flex flex-col items-center justify-center" :class="boxWrapperClass">
            <!-- Border Box -->
            <div class="w-full rounded bg-none dark:border-gray-700 light:border-gray-200" :class="boxBorderClass">
                <!-- Header -->
                <div class="space-y-3" :class="boxHeaderClass">
                    <div v-if="header || subheader || headerSlotAvailable" class="flex items-center bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-600" :class="boxHeaderWrapperClass">
                        <div :class="boxHeaderSizeClass">
                            <div class="flex items-center">
                                <div class="flex flex-col justify-start">
                                    <div class="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
                                        <Transition
                                            name="fade-fast"
                                            mode="out-in"
                                            :duration="{
                                                enter: 300,
                                                leave: 300,
                                            }"
                                            v-if="transition">
                                            <span :key="header">
                                                {{ header ?? "" }}
                                            </span>
                                        </Transition>
                                        <span v-else>
                                            {{ header ?? "" }}
                                        </span>
                                    </div>
                                    <div class="text-sm font-semibold leading-tight tracking-tight text-gray-900 md:text-md dark:text-gray-400">
                                        <Transition
                                            name="fade-fast"
                                            mode="out-in"
                                            :duration="{
                                                enter: 300,
                                                leave: 300,
                                            }"
                                            v-if="transition">
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
                    </div>
                    <!-- <hr v-if="header || subheader || headerSlotAvailable" class="border-gray-200 dark:border-gray-700 hidden" :class="boxHRClass" /> -->
                </div>

                <!-- Content -->
                <div :class="boxContentClass">
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
        boxView: {
            type: Boolean,
            default: true,
        },
        contentConform: {
            type: Boolean,
            default: true,
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
        boxPageClass() {
            return this.boxView ? "max-w-screen-xl mx-auto md:px-10" : "";
        },
        boxWrapperClass() {
            return this.boxView ? "md:pt-8" : "";
        },
        boxBorderClass() {
            return this.boxView ? "md:border md:p-8" + " " + this.class : "";
        },
        boxHeaderClass() {
            return this.boxView ? "md:space-y-4 md:pb-6" : "";
        },
        boxHeaderWrapperClass() {
            return this.boxView ? "justify-between" : "justify-center";
        },
        boxHeaderInsideClass() {
            return this.boxView ? "md:p-0 md:border-none" : "";
        },
        boxHeaderSizeClass() {
            return (!this.boxView ? "w-full max-w-screen-xl flex flex-row justify-between p-4" : "p-4 md:pb-4 md:p-0") + " " + "flex flex-row justify-between w-full";
        },
        boxHRClass() {
            return this.boxView ? "md:block" : "";
        },
        boxContentClass() {
            return (this.boxView ? "md:p-0 p-4" : "pt-6 px-4") + " " + (this.contentConform ? "w-full max-w-screen-xl m-auto" : "");
        },
    },
});
</script>
