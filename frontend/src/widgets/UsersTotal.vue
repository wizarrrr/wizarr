<template>
    <WidgetTemplate :title="__('Total Users')" :value="count" icon="fa-user" />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useUsersStore } from "@/stores/users";

import WidgetTemplate from "@/templates/WidgetTemplate.vue";

export default defineComponent({
    name: "UsersTotal",
    components: {
        WidgetTemplate,
    },
    computed: {
        count() {
            return String(this.users.length);
        },
        ...mapState(useUsersStore, ["users"]),
    },
});
</script>
