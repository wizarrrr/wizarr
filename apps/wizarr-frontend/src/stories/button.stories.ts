import type { Meta, StoryObj } from "@storybook/vue3";

import Button from "./Button.vue";

const meta: Meta<typeof Button> = {
    title: "Button",
    component: Button,
    argTypes: {
        dataTheme: {
            options: ["primary", "secondary", "success", "danger", "warning", "transparent", "none"],
            control: {
                type: "select",
            },
        },
        onClick: {
            action: "onClick",
        },
    },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {
    args: {
        label: "Primary",
        dataTheme: "primary",
    },
};

export const Secondary: Story = {
    args: {
        label: "Secondary",
        dataTheme: "secondary",
    },
};

export const Success: Story = {
    args: {
        label: "Success",
        dataTheme: "success",
    },
};

export const Danger: Story = {
    args: {
        label: "Danger",
        dataTheme: "danger",
    },
};

export const Warning: Story = {
    args: {
        label: "Warning",
        dataTheme: "warning",
    },
};

export const Transparent: Story = {
    args: {
        label: "Transparent",
        dataTheme: "transparent",
    },
};

export const None: Story = {
    args: {
        label: "None",
        dataTheme: "none",
    },
};
