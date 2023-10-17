<template>
    <div class="flex flex-col space-y-4">
        <p class="text-gray-500 dark:text-gray-300">
            {{ __("We're here to help you with any issues or questions you may have. If you require assistance, paying members can use the button below to begin a live support session with a Wizarr assistant and we will attempt to guide you through any issues you may be having and resolve them.") }}
        </p>
        <FormKit type="button" @click="startSupportSession">
            {{ __("Start Support Session") }}
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/stores/user";
import { mapState } from "pinia";

export default defineComponent({
    name: "Support",
    computed: {
        ...mapState(useUserStore, ["user"]),
    },
    methods: {
        async startSupportSession() {
            // Confirm with user that they wish to start a support session
            const confirm = await this.$modal.confirmModal(this.__("Start Support Session"), this.__("Are you sure you wish to start a support session?"), { confirmButtonText: this.__("Yes") });

            // If user doesn't confirm, don't continue
            if (!confirm) return;

            // Redirect to support page
            const support = new this.$RocketChat("https://livechat.wizarr.dev");

            support.setGuestName(this.user?.display_name ?? "Unknown");
            support.setGuestEmail(this.user?.email ?? "Unknown");

            // // Open support session
            support.maximizeWidget();
            support.onChatEnded(() => {
                support.closeWidget();
                document.getElementsByClassName("rocketchat-widget")[0].remove();
                this.$toast.info(this.__("Support session ended"));
            });
        },
    },
});
</script>
