<template>
    <div
        class="text-sm font-medium text-center text-gray-500 border-b border-gray-200 dark:text-gray-400 dark:border-gray-700"
    >
        <ul class="flex flex-wrap -mb-px">
            <template v-for="(tab, index) in tabbedTabs">
                <template v-if="!tab.hidden">
                    <button
                        @click="currentTab = index"
                        class="first:pl-[1.5rem] last:pr-[1.5rem] cursor-pointer"
                        :class="
                            currentTab === index
                                ? tabClasses.active
                                : tabClasses.inactive
                        "
                        :disabled="tab.disabled"
                    >
                        <i :class="`fa-solid ${tab.icon} mr-2`"></i>
                        <span>{{ tab.name }}</span>
                    </button>
                </template>
            </template>
        </ul>
    </div>

    <div v-bind="$attrs">
        <template v-for="(tab, index) in tabbedTabs">
            <template v-if="currentTab == index && tab.asyncComponent">
                <component v-bind="{ ...tab.props }" :is="tab.asyncComponent" />
            </template>
        </template>
    </div>
</template>

<script lang="ts">
import { defineComponent, defineAsyncComponent } from 'vue';

import type { Component } from 'vue';

type Tab = {
    name: string;
    icon: string;
    props?: Record<string, any>;
    disabled?: boolean;
    hidden?: boolean;
    component: () => Promise<Component>;
    asyncComponent?: Component;
};

export default defineComponent({
    name: 'UserManager',
    props: {
        tabs: {
            type: Array as () => Tab[],
            required: true,
        },
    },
    data() {
        return {
            currentTab: 0,
            tabbedTabs: [] as Tab[],
            tabClasses: {
                active: 'inline-block p-4 text-gray-600 border-b-2 border-gray-600 rounded-t-lg active dark:text-gray-300 dark:border-gray-300',
                inactive:
                    'inline-block p-4 border-b-2 border-transparent rounded-t-lg hover:text-gray-300 hover:border-gray-300 dark:hover:text-gray-300',
            },
        };
    },
    methods: {
        asyncComponent(component: Tab['component']) {
            return defineAsyncComponent({
                loader: component,
            });
        },
        mapViews() {
            return this.tabs.map((view) => {
                return {
                    ...view,
                    asyncComponent: this.asyncComponent(view.component),
                };
            });
        },
    },
    mounted() {
        this.tabbedTabs = this.mapViews();
    },
});
</script>
