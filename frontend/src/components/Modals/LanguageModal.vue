<template>
    <DefaultModal titleString="Select Language">
        <template #body>
            <div class="grid grid-cols-2 gap-2">
                <template v-for="(_, index) in availableLanguages" :key="language">
                    <button class="py-2 px-3 space-x-3 flex items-center justify-start rounded border border-gray-700 hover:bg-gray-200 hover:dark:bg-gray-700" @click="languageSelected(index)" :class="language === index ? 'bg-gray-200 dark:bg-gray-700' : ''">
                        <span :class="'fi' + ` fi-${index}`"></span>
                        <span>{{ availableLanguages[index] }}</span>
                    </button>
                </template>
            </div>
        </template>
    </DefaultModal>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useLanguageStore } from "@/stores/language";
import { mapState } from "pinia";

import DefaultModal from "../Modals/DefaultModal.vue";
import { mapActions } from "pinia";

export default defineComponent({
    name: "LanguageSelector",
    components: {
        DefaultModal,
    },
    computed: {
        ...mapState(useLanguageStore, ["language", "availableLanguages"]),
    },
    methods: {
        languageSelected(index: string | number) {
            this.setLanguage(String(index));
            this.$emit("close");
        },
        ...mapActions(useLanguageStore, ["setLanguage"]),
    },
    mounted() {
        console.log(this.language);
    },
});
</script>
