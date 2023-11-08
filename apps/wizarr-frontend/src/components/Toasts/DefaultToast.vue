<script lang="ts">
import { defineComponent, h } from "vue";

// A function that generates the component and returns it
const generateComponent = (title: string, message: string) => {
    return defineComponent({
        name: title,
        data() {
            return {
                title,
                message,
            };
        },
        render() {
            return h("div", { class: "flex flex-col justify-start items-start" }, [
                h(
                    "span",
                    {
                        class: "text-md font-semibold text-gray-900 dark:text-white",
                    },
                    this.title,
                ),
                h("span", { class: "text-sm text-gray-900 dark:text-white" }, this.message),
            ]);
        },
    });
};

// Export the generated component
export default generateComponent;
</script>
