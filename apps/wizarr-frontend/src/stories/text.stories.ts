import type { Meta, StoryObj } from "@storybook/vue3";

import Text from "./Text.vue";

const meta: Meta<typeof Text> = {
    title: "Text",
    component: Text,
};

export default meta;
type Story = StoryObj<typeof Text>;

export const Default: Story = {
    args: {},
};
