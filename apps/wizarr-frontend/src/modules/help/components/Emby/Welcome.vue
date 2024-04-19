<template>
    <div class="flex flex-col space-y-4">
        <div>
            <h4 class="mb-3 text-xl font-bold dark:text-white">ℹ️ {{ __("Eh, So, What is Emby exactly?") }}</h4>
            <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
                {{ __("Emby is a platform that lets you stream all your favorite movies, TV shows, and music in one place. It's like having your own personal movie theater right at your fingertips! Think of it as a digital library of your favorite content that you can access from anywhere, on any device - your phone, tablet, laptop, smart TV, you name it.") }}
            </p>
        </div>
        <div>
            <h4 class="mb-3 text-xl font-bold dark:text-white">🍿 {{ __("Right, so how do I watch stuff?") }}</h4>
            <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
                {{ __("It couldn't be simpler! Emby is available on a wide variety of devices including laptops, tablets, smartphones, and TVs. All you need to do is download the Emby app on your device, sign in with your account, and you're ready to start streaming your media. It's that easy!") }}
            </p>
        </div>
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
