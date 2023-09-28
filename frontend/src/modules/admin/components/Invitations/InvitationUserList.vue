<template>
    <SimpleUserList :users="users" />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import type { Users } from "@/types/api/users";

import SimpleUserList from "./SimpleUserList/SimpleUserList.vue";

export default defineComponent({
    name: "InvitationUserList",
    components: {
        SimpleUserList,
    },
    props: {
        users: {
            type: Array as () => Users,
            required: true,
        },
    },
});
</script>
