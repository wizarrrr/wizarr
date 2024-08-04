<template>
    <DropdownToolbar :title="__('Variables')" :visible="state.visible" @change="onChange">
        <template #trigger>
            <span>{}</span>
        </template>
        <template #overlay>
            <div class="md-editor-dropdown-overlay">
                <ol class="md-editor-menu">
                    <li v-for="variable in variables" :key="`variable-${variable}`" @click="variableHandler(variable)" v-html="variable" class="md-editor-menu-item"></li>
                </ol>
            </div>
        </template>
    </DropdownToolbar>
</template>

<script lang="ts">
import { defineComponent, reactive } from "vue";
import { DropdownToolbar } from "md-editor-v3";
import type { Insert, InsertContentGenerator } from "md-editor-v3";
import type { PropType } from "vue";

export default defineComponent({
    name: "VariablesToolbar",
    components: {
        DropdownToolbar,
    },
    props: {
        insert: {
            type: Function as PropType<Insert>,
            default: () => null,
        },
        variables: {
            type: Array as PropType<Array<string>>,
            default: () => [],
        },
    },
    setup(props) {
        const state = reactive({
            visible: false,
        });

        const variableHandler = (variable: string) => {
            const generator: InsertContentGenerator = () => ({
                targetValue: `{{${variable}}}`,
                select: true,
                deviationStart: 0,
                deviationEnd: 0,
            });

            props.insert(generator);
        };

        const onChange = (visible: boolean) => {
            state.visible = visible;
        };

        return {
            state,
            variableHandler,
            onChange,
        };
    },
});
</script>
