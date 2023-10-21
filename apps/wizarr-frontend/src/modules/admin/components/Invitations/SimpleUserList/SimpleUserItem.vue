<template>
    <div
        class="flex flex-row text-gray-900 overflow-hidden px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-white transition duration-150 ease-in-out"
    >
        <div
            class="flex flex-grow items-center justify-start space-x-0 md:space-x-3 w-2/3"
        >
            <div
                class="aspect-square h-full hidden md:flex items-center justify-center"
            >
                <div
                    class="flex-shrink-0 h-[60px] w-[60px] rounded bg-gray-50 overflow-hidden"
                >
                    <img
                        :src="profilePicture"
                        :onerror="`this.src='${backupPicture}'`"
                        class="w-full h-full object-cover object-center"
                        alt="Profile Picture"
                    />
                </div>
            </div>
            <div
                class="dark:text-white font-bold flex flex-col items-start justify-between w-full overflow-hidden truncate"
            >
                <span class="text-lg">{{ user.username }}</span>
                <div class="flex flex-col">
                    <p
                        v-if="user.email"
                        class="text-xs truncate text-gray-500 dark:text-gray-400 w-full"
                    >
                        {{ user.email }}
                    </p>
                    <p
                        v-else
                        class="text-xs truncate text-gray-500 dark:text-gray-400 w-full"
                    >
                        No email
                    </p>
                    <p
                        v-if="user.expires"
                        class="text-xs truncate w-full"
                        :class="color"
                    >
                        {{ expired }}
                    </p>
                    <p
                        v-else
                        class="text-xs truncate text-gray-500 dark:text-gray-400 w-full"
                    >
                        {{ $filter('timeAgo', user.created) }}
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import type { User } from '@/types/api/users';

import ListItem from '@/components/ListItem.vue';

export default defineComponent({
    name: 'SimpleUserItem',
    components: {
        ListItem,
    },
    props: {
        user: {
            type: Object as () => User,
            required: true,
        },
    },
    data() {
        return {
            profilePicture:
                'https://ui-avatars.com/api/?uppercase=true&name=' +
                this.user.username +
                '&length=1',
            backupPicture:
                'https://ui-avatars.com/api/?uppercase=true&name=' +
                this.user.username +
                '&length=1',
        };
    },
    computed: {
        expired(): string {
            if (this.$filter('isPast', this.user.expires!)) {
                return this.__('Expired %{s}', {
                    s: this.$filter('timeAgo', this.user.expires!),
                });
            } else {
                return this.__('Expires %{s}', {
                    s: this.$filter('timeAgo', this.user.expires!),
                });
            }
        },
        color() {
            const inHalfDay = new Date();
            inHalfDay.setHours(inHalfDay.getHours() + 12);

            if (this.$filter('isPast', this.user.expires!)) {
                return 'text-red-600 dark:text-red-500';
            }

            if (this.$filter('dateLess', this.user.expires!, inHalfDay)) {
                return 'text-yellow-500 dark:text-yellow-400';
            }

            return 'text-gray-500 dark:text-gray-400';
        },
    },
    methods: {
        async getProfilePicture() {
            const response = this.$axios.get(
                `/api/users/${this.user.token}/profile-picture`,
                {
                    responseType: 'blob',
                },
            );

            this.profilePicture = URL.createObjectURL((await response).data);
        },
    },
    mounted() {
        this.getProfilePicture();
    },
});
</script>
