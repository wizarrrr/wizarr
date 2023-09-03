<script lang="ts">
import { defineComponent, reactive } from "vue";
import { useNetwork } from "@vueuse/core";

import type { ToastOptions, ToastID } from "vue-toastification/dist/types/types";

import DefaultToast from "@/components/Toasts/DefaultToast.vue";

export default defineComponent({
    data() {
        return {
            offlineToast: DefaultToast("Connection Offline", "You are offline, check your connection."),
            onlineToast: DefaultToast("Connection Online", "You are back online."),
            toastOptions: {
                timeout: false,
                closeButton: false,
                draggable: false,
                closeOnClick: false,
            } as ToastOptions,
            useNetwork: reactive(useNetwork()),
            toast: null as ToastID | null,
        };
    },
    render() {
        return null;
    },
    watch: {
        "useNetwork.isOnline": {
            immediate: false,
            handler(isOnline) {
                if (isOnline) {
                    this.$toast.dismiss(this.toast as ToastID);
                    this.toast = this.$toast.success(this.onlineToast);
                } else {
                    this.$toast.dismiss(this.toast as ToastID);
                    this.toast = this.$toast.error(this.offlineToast, this.toastOptions);
                }
            },
        },
    },
});
</script>
