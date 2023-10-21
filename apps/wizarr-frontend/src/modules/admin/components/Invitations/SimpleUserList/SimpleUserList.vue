<template>
    <div
        class="flex flex-col m-[-1.5rem] divide-y divide-gray-200 dark:divide-gray-700"
    >
        <template v-for="user in users">
            <SimpleUserItem :user="user" />
        </template>
        <div
            v-if="users && users.length === 0"
            class="flex flex-col justify-center items-center space-y-1 py-4"
        >
            <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
            <span class="text-gray-400">{{ __('No Users found') }}</span>
            <span class="text-gray-600 text-xs">{{
                __('Deleted users will not be visible')
            }}</span>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import type { Users } from '@/types/api/users';

import SimpleUserItem from './SimpleUserItem.vue';

export default defineComponent({
    name: 'UserList',
    components: {
        SimpleUserItem,
    },
    props: {
        users: {
            type: Array as () => Users,
            required: true,
        },
    },
});
</script>
