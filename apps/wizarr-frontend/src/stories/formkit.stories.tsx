import type { Meta, StoryObj } from "@storybook/vue3";
import type { FormKitInputs } from "@formkit/inputs";
import type { AllowedComponentProps, RendererElement, RendererNode, VNode, VNodeProps, ComponentCustomProps } from "vue";

import { defineComponent } from "vue";
import { FormKit, type FormKitSetupContext } from "@formkit/vue";

export declare type FormKitComponentButtonProps = {
    type: "button" | "submit" | "reset";
    label: string;
    "data-theme": "primary" | "secondary" | "success" | "danger" | "warning" | "transparent" | "none";
    onClick: () => void;
};

export declare type FormKitComponent = <Props extends FormKitInputs<Props>>(
    props: Props & VNodeProps & AllowedComponentProps & ComponentCustomProps & FormKitComponentButtonProps,
    context?: Pick<FormKitSetupContext<Props>, "attrs" | "emit" | "slots">,
    setup?: FormKitSetupContext<Props>,
) => VNode<
    RendererNode,
    RendererElement,
    {
        [key: string]: any;
    }
> & {
    __ctx?: FormKitSetupContext<Props>;
};

// type FormKitComponentAndCustomArgs = FormKitComponent<typeof globalArgs>;

const meta: Meta<FormKitComponent> = {
    title: "FormKit",
    component: defineComponent({
        render() {
            return <FormKit {...this.$attrs} />;
        },
    }),
};

export default meta;
type Story = StoryObj<FormKitComponent>;

const globalArgs: Story["args"] = {
    label: "Label",
    help: "",
};

export const Button: Story = {
    args: {
        type: "button",
        "data-theme": "primary",
        ...globalArgs,
    },
    argTypes: {
        "data-theme": {
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

export const Text: Story = {
    args: {
        type: "text",
        placeholder: "Placeholder",
        ...globalArgs,
    },
    argTypes: {
        type: {
            options: ["text", "email", "password", "number", "tel", "url", "search", "textarea"],
            control: {
                type: "select",
            },
        },
    },
};

export const Select: Story = {
    args: {
        type: "select",
        options: ["Option 1", "Option 2", "Option 3"] as any,
        ...globalArgs,
    },
    argTypes: {
        options: {
            control: {
                type: "array",
            },
        },
    },
};

export const Checkbox: Story = {
    args: {
        type: "checkbox",
        ...globalArgs,
    },
};

export const Radio: Story = {
    args: {
        type: "radio",
        options: ["Option 1", "Option 2", "Option 3"] as any,
        ...globalArgs,
    },
};

export const Toggle: Story = {
    args: {
        type: "toggle",
        ...globalArgs,
    },
};

export const Rating: Story = {
    args: {
        type: "rating",
        ...globalArgs,
    },
};

export const Range: Story = {
    args: {
        type: "range",
        ...globalArgs,
    },
};
