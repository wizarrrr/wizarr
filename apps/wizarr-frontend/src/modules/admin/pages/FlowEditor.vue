<template>
    <HeaderTemplate
        :header="__('Flow Editor')"
        :subheader="__('Manage your command flows')"
    >
        <template #header>
            <DefaultButton theme="primary">
                {{ __('Create Flow') }}</DefaultButton
            >
        </template>
        <template #default>
            <VueFlow v-model="elements" fit-view-on-init disabled>
                <Controls />
                <MiniMap />
                <Background :gap="12" :size="1" />
            </VueFlow>
        </template>
    </HeaderTemplate>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { VueFlow } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { MiniMap } from '@vue-flow/minimap';
import { Controls } from '@vue-flow/controls';

import HeaderTemplate from '@/templates/HeaderTemplate.vue';
import DefaultButton from '@/components/Buttons/DefaultButton.vue';

const initialElements = [
    // Nodes
    {
        id: '1',
        label: 'This page is still under testing',
        position: { x: 400, y: 100 },
        class: 'light',
    },
    {
        id: '2',
        label: 'there is currently not functionality',
        position: { x: 400, y: 300 },
        class: 'light',
    },

    // Edges
    {
        id: 'e1-2',
        source: '1',
        target: '2',
        type: 'smoothstep',
        animated: true,
    },
];

export default defineComponent({
    name: 'FlowEditorView',
    components: {
        VueFlow,
        Background,
        MiniMap,
        Controls,
        HeaderTemplate,
        DefaultButton,
    },
    data() {
        return {
            elements: initialElements,
        };
    },
    mounted() {
        // setInterval(() => {
        // Move first element around in a circle.
        //     this.elements = this.elements.map((el) => {
        //         if (el.id === "1") {
        //             const newX = 400 + 100 * Math.cos(Date.now() / 1000);
        //             const newY = 100 + 100 * Math.sin(Date.now() / 1000);
        //             return {
        //                 ...el,
        //                 position: {
        //                     x: newX,
        //                     y: newY,
        //                 },
        //             };
        //         }
        //         return el;
        //     });
        // }, 1);
    },
});
</script>
