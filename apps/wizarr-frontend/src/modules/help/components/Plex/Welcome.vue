<template>
    <div>
        <h4 class="mb-3 text-xl font-bold dark:text-white">ℹ️ {{ __("Eh, So, What is Plex exactly?") }}</h4>
        <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
            {{ __("Great question! Plex is a software that allows individuals to share their media collections with others. If you've received this invitation, it means someone wants to share their library with you.") }}
        </p>
        <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
            {{ __("With Plex, you'll have access to all of the movies, TV shows, music, and photos that are stored on their server!") }}
        </p>
        <p class="font-normal text-gray-700 dark:text-gray-400">
            {{ __("So let's see how to get started!") }}
        </p>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Welcome",
    mounted() {
        this.$emit("height");
    },
});
</script>
