<template>
    <div>
        <div class="grid-stack mx-[-10px]">
            <!-- Revert .filter() once we have working firebase access to re-enable LatestInfo widget -->
            <Widget v-for="widget in dashboard.filter((widget) => widget.type !== 'LatestInfo')" :key="widget.id" :data="widget" :isEditing="isEditing" @delete="deleteLocalWidget" />
        </div>
        <Transition name="fade" mode="out-in" :duration="{ enter: 100, leave: 100 }">
            <div v-if="isEditing" class="fixed right-6 bottom-6 group" @mouseover="isShowing = true" @mouseleave="isShowing = false">
                <div class="flex flex-col items-center mb-4 space-y-2" :class="{ hidden: !isShowing }">
                    <button @click="resetLocalDashboard" type="button" class="relative w-14 h-14 text-gray-500 bg-white rounded border border-gray-200 hover:text-gray-900 dark:border-gray-600 shadow-sm dark:hover:text-white dark:text-gray-400 hover:bg-gray-50 dark:bg-gray-700 dark:hover:bg-gray-600">
                        <i class="fas fa-trash-alt"></i>
                        <span class="absolute block mb-px text-sm font-medium -translate-y-1/2 -left-[110px] top-1/2">
                            {{ __("Reset Layout") }}
                        </span>
                    </button>
                </div>
                <FormKit type="button" :classes="{ input: '!w-14 !h-14' }">
                    <i class="fas fa-plus text-xl transition-transform group-hover:rotate-45"></i>
                </FormKit>
            </div>
        </Transition>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { GridStack } from "gridstack";
import { mapWritableState, mapActions } from "pinia";
import { useDashboardStore } from "@/stores/dashboard";

import Widget from "./Widget.vue";

import "gridstack/dist/gridstack.min.css";
import "gridstack/dist/gridstack-extra.min.css";

import type { GridStackOptions } from "gridstack";
import type { WidgetOptions } from "@/types/local/WidgetOptions";

export default defineComponent({
    name: "Dashboard",
    components: {
        Widget,
    },
    props: {
        isEditing: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            grid: null as GridStack | null,
            gridOptions: {
                column: 6,
                cellHeight: 70,
                margin: 10,
                disableResize: true,
                disableDrag: !this.isEditing,
            } as GridStackOptions,
            isEditing: this.isEditing,
            isShowing: false,
        };
    },
    computed: {
        ...mapWritableState(useDashboardStore, ["dashboard"]),
    },
    methods: {
        makeWidgets(widgets: WidgetOptions[]) {
            widgets.forEach((widget) => {
                if (widget.type === "LatestInfo") return;
                this.makeWidget(widget);
            });
        },
        makeWidget(item: WidgetOptions) {
            const elSelector = `#${item.id}`;
            return this.grid?.makeWidget(elSelector);
        },
        deleteLocalWidget(id: string) {
            this.grid?.removeWidget(`#${id}`);
        },
        async resetLocalDashboard() {
            if (await this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to reset your dashboard?"))) {
                this.resetDashboard();
                this.grid?.removeAll();
                this.isEditing = false;
                this.$emit("update:isEditing", this.isEditing);
                setTimeout(async () => await new Promise(() => this.makeWidgets(this.dashboard)).catch(() => window.location.reload()));
                this.$toast.info(this.__("Dashboard reset successfully"));
            } else {
                this.$toast.info(this.__("Dashboard reset cancelled"));
            }
        },
        ...mapActions(useDashboardStore, ["resetDashboard"]),
    },
    watch: {
        isEditing: {
            immediate: true,
            handler(isEditing: boolean) {
                this.grid?.enableMove(isEditing);
            },
        },
    },
    mounted() {
        this.grid = GridStack.init(this.gridOptions);
        this.makeWidgets(this.dashboard);
    },
});
</script>
