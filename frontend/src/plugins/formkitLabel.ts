import type { FormKitPlugin } from "@formkit/core";

const isCheckboxAndRadioMultiple: FormKitPlugin = (node) => (node.props.type === "checkbox" || node.props.type === "radio") && node.props.options;

const formkitLabelPlugin: FormKitPlugin = (node) => {
    node.on("created", () => {
        const isRequired = node.props.parsedRules.some((rule: any) => rule.name === "required");
        if (!isRequired) return;

        console.log(node);

        const isMultiOption = isCheckboxAndRadioMultiple(node);
        node.props.definition!.schemaMemoKey = `required_${isMultiOption ? "multi_" : ""}${node.props.definition!.schemaMemoKey}`;

        const schemaFn = node.props.definition!.schema;
        node.props.definition!.schema = (sectionsSchema = {}) => {
            if (isRequired) {
                if (isMultiOption) {
                    sectionsSchema.legend = {
                        children: ["$label", "*"],
                    };
                } else {
                    sectionsSchema.label = {
                        children: ["$label", "*"],
                    };
                }
            }
            // @ts-ignore
            return schemaFn(sectionsSchema);
        };
    });
};

export default formkitLabelPlugin;
