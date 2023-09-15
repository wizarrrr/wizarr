<template>
    <div class="grid-stack mx-[-10px]">
        <Widget v-for="widget in dashboard" :key="widget.id" :data="widget" :is-editing="isEditing" @delete="deleteWidget" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { GridStack } from "gridstack";
import { mapWritableState } from "pinia";
import { useDashboardStore } from "@/stores/dashboard";

import Widget from "./Widget.vue";
import Button from "./Button.vue";

import "gridstack/dist/gridstack.min.css";
import "gridstack/dist/gridstack-extra.min.css";

import type { GridStackOptions } from "gridstack";
import type { WidgetOptions } from "@/types/local/WidgetOptions";

export default defineComponent({
    name: "Dashboard",
    components: {
        Widget,
        Button,
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
        };
    },
    computed: {
        ...mapWritableState(useDashboardStore, ["dashboard"]),
    },
    methods: {
        makeWidgets(widgets: WidgetOptions[]) {
            widgets.forEach((widget) => {
                this.makeWidget(widget);
            });
        },
        makeWidget(item: WidgetOptions) {
            const elSelector = `#${item.id}`;
            return this.grid?.makeWidget(elSelector);
        },
        deleteWidget(id: string) {
            this.grid?.removeWidget(`#${id}`);
        },
    },
    watch: {
        isEditing: {
            immediate: true,
            handler(isEditing: boolean) {
                this.grid?.enableMove(isEditing);
            },
        },
        dashboard: {
            immediate: true,
            handler(dashboard: WidgetOptions[]) {
                console.log(dashboard);
            },
            deep: true,
        },
    },
    mounted() {
        this.grid = GridStack.init(this.gridOptions);
        this.makeWidgets(this.dashboard);
    },
});
</script>
