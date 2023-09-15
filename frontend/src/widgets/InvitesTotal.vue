<template>
    <WidgetTemplate :title="__('Total Invites')" :value="count" icon="fa-envelope" />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useInvitationStore } from "@/stores/invitations";
import { mapState } from "pinia";

import WidgetTemplate from "@/templates/WidgetTemplate.vue";

export default defineComponent({
    name: "InvitesTotal",
    components: {
        WidgetTemplate,
    },
    computed: {
        count() {
            return String(this.invitations.length);
        },
        ...mapState(useInvitationStore, ["invitations"]),
    },
});
</script>
