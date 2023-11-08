<template>
    <div :class="widgetClassName" :ref="localData.id" :id="localData.id" :gs-id="localData.id" :gs-x="localData.grid.x" :gs-y="localData.grid.y" :gs-w="localData.grid.w" :gs-h="localData.grid.h">
        <div class="grid-stack-item-content group border dark:border-gray-700 relative p-4 text-gray-900 dark:text-gray-200 bg-white dark:bg-gray-800 highlight-white/5 rounded shadow-md flex items-center justify-center" :class="{ 'cursor-move': isEditing }">
            <Transition name="fade" mode="out-in" :duration="{ enter: 100, leave: 100 }">
                <component v-if="component" :is="component" :data="data" :isEditing="isEditing" :class="{ 'group-hover:!opacity-100': isEditing }" />
            </Transition>
            <DeleteButton v-if="isEditing" class="opacity-0 group-hover:opacity-100 transition duration-300 ease-in-out absolute top-2 right-2" @click="deleteWidget(localData.id)" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapActions } from "pinia";
import { useDashboardStore } from "@/stores/dashboard";
import { getWidget } from "@/ts/utils/widgets";

import type { WidgetOptions } from "@/types/local/WidgetOptions";

import DeleteButton from "./DeleteButton.vue";

export default defineComponent({
    name: "Widget",
    components: {
        DeleteButton,
    },
    props: {
        data: {
            type: Object as () => WidgetOptions,
            required: true,
        },
        isEditing: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            localData: this.data,
            component: getWidget(this.data.type),
        };
    },
    computed: {
        widgetClassName(): string {
            return this.localData.type
                .replace(/([A-Z])/g, "-$1")
                .toLowerCase()
                .substring(1);
        },
    },
    watch: {
        isEditing: {
            immediate: false,
            handler() {
                if (!this.isEditing) {
                    const el = this.$refs[this.localData.id] as HTMLElement;

                    const x = el.getAttribute("gs-x");
                    const y = el.getAttribute("gs-y");
                    const w = el.getAttribute("gs-w");
                    const h = el.getAttribute("gs-h");

                    this.updateWidget({
                        ...this.localData,
                        grid: {
                            x: x ? parseInt(x) : 0,
                            y: y ? parseInt(y) : 0,
                            w: w ? parseInt(w) : 0,
                            h: h ? parseInt(h) : 0,
                        },
                    });
                }
            },
        },
    },
    methods: {
        ...mapActions(useDashboardStore, ["updateWidget", "deleteWidget"]),
    },
});
</script>
