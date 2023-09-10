<template>
    <div class="flex flex-col justify-center items-start space-y-2">
        <p class="w-full text-sm font-medium text-gray-900 dark:text-white">
            {{ __("You're all set, click continue to get started and walkthrough how to use %{serverName}!", { serverName: $filter("firstLetterUppercase", settings.server_type) }) }}
        </p>
        <FormKit type="button" @click="$router.push('/help')">
            {{ __("Continue") }}
        </FormKit>
    </div>
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";

export default defineComponent({
    name: "JoinCompleteView",
    computed: {
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
