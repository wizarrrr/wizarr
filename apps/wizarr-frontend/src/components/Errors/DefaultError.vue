<script lang="ts">
import { defineComponent, h } from "vue";

const generateComponent = (title: string, message: string, icon?: string) => {
    return defineComponent({
        name: title,
        data() {
            return {
                title,
                message,
                icon,
            };
        },
        render() {
            const title = h(
                "span",
                {
                    class: "text-md font-semibold text-gray-900 dark:text-white",
                },
                this.title,
            );
            const message = h("span", { class: "text-sm text-gray-900 dark:text-white" }, this.message);
            const icon = h("i", {
                class: this.icon ?? "fas fa-exclamation-triangle text-yellow-500 dark:text-yellow-400",
            });

            const iconSpan = h(
                "span",
                {
                    class: "flex justify-center align-center text-md w-[40px] text-4xl font-semibold text-gray-900 dark:text-white",
                },
                icon,
            );

            const childDiv = h("div", { class: "ml-2 flex flex-col justify-start items-start" }, [title, message]);
            const parentDiv = h("div", { class: "flex flex-row justify-start items-center" }, [iconSpan, childDiv]);

            return parentDiv;
        },
    });
};

export default generateComponent;
</script>
