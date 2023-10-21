<template>
    <div>
        <h4 class="mb-3 text-xl font-bold dark:text-white">
            ℹ️ {{ __('Eh, So, What is Jellyfin exactly?') }}
        </h4>
        <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
            {{
                __(
                    "Jellyfin is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It's like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.",
                )
            }}
        </p>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'Welcome',
    mounted() {
        this.$emit('height');
    },
});
</script>
