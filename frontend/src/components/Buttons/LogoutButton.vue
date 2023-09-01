<template>
    <div class="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
        <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="logout">
            <i class="fa-solid fa-lg fa-right-from-bracket"></i>
        </button>
    </div>
</template>

<script lang="ts">
import { useUserStore } from "@/stores/user";
import { defineComponent } from "vue";
import { mapActions } from "pinia";

export default defineComponent({
    name: "LogoutButton",
    methods: {
        ...mapActions(useUserStore, ["logout"]),
    },
});
</script>
