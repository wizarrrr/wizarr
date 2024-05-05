<template>
    <Draggable :disabled="isDisabled" v-if="users && users.length > 0" v-model="users" tag="ul" group="users" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element, index }">
            <li class="mb-2">
                <UserItem :user="element" :count="index" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center space-y-1">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __("No Users found") }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUsersStore } from "@/stores/users";
import { mapActions, mapWritableState } from "pinia";
import { usePointer } from "@vueuse/core";

import Draggable from "vuedraggable";
import UserItem from "./UserItem.vue";

export default defineComponent({
    name: "UserList",
    components: {
        Draggable,
        UserItem,
    },
    data() {
        return {
            pointer: usePointer(),
        };
    },
    computed: {
        isDisabled() {
            return this.pointer.pointerType !== "mouse" || false;
        },
        ...mapWritableState(useUsersStore, ["users"]),
    },
    methods: {
        ...mapActions(useUsersStore, ["getUsers"]),
    },
    async created() {
        await this.getUsers();
    },
});
</script>
