<template>
    <Draggable v-model="users" tag="ul" group="users" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <UserItem :user="element" />
            </li>
        </template>
    </Draggable>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUsersStore } from "@/stores/users";
import { mapActions, mapWritableState } from "pinia";

import Draggable from "vuedraggable";
import UserItem from "./UserItem.vue";

export default defineComponent({
    name: "UserList",
    components: {
        Draggable,
        UserItem,
    },
    computed: {
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
