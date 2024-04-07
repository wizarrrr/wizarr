<template>
    <div>
        <h1
            class="text-xl text-center font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
            {{ __('Database') }}
        </h1>
        <p class="text-base text-center text-gray-700 dark:text-gray-400 md:text-md">
            {{
            __(
            "Currently Wizarr only supports it's internal SQLite database.",
            )
            }}
            <br />
            {{
            __(
                'This is a temporary, and we are working on adding support for other databases.',
            )
}}
        </p>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'DatabaseView',
});
</script>
