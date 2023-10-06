<template>
    <div class="grid grid-cols-2 gap-2">
        <template v-for="(_, index) in availableLanguages" :key="language">
            <button class="py-2 px-3 space-x-3 flex items-center justify-start rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-200 hover:dark:bg-gray-700" @click="languageSelected(index)" :class="language === index ? 'bg-gray-200 dark:bg-gray-700' : ''">
                <span :class="'fi' + ` fi-${index}`"></span>
                <span>{{ availableLanguages[index] }}</span>
            </button>
        </template>
        <button class="py-2 px-3 space-x-3 flex items-center justify-start rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-200 hover:dark:bg-gray-700" @click="languageSelected('auto')" :class="language === 'auto' ? 'bg-gray-200 dark:bg-gray-700' : ''">
            <i class="fa-solid fa-md fa-globe"></i>
            <span>{{ __("System Default") }}</span>
        </button>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState, mapActions } from "pinia";
import { useLanguageStore } from "@/stores/language";

export default defineComponent({
    name: "LanguageSelector",
    computed: {
        ...mapState(useLanguageStore, ["language", "availableLanguages"]),
    },
    methods: {
        languageSelected(index: string | number) {
            this.setLanguage(String(index));
            this.$parent!.$emit("close");
        },
        ...mapActions(useLanguageStore, ["setLanguage"]),
    },
});
</script>
