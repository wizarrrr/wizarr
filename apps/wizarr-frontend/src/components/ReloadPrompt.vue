<script lang="ts">
import { defineComponent } from "vue";
import { useRegisterSW } from "virtual:pwa-register/vue";
// @ts-ignore
import { pwaInfo } from "virtual:pwa-info";

export default defineComponent({
    name: "ReloadPrompt",
    data() {
        return {
            pwaInfo: pwaInfo,
            offlineReady: false,
            needRefresh: false,
        };
    },
    methods: {
        onRegisteredSW(swScriptUrl: string, registration: ServiceWorkerRegistration | undefined) {
            console.log("\x1b[34m[SW]\x1b[32m Service Worker Registered\x1b[33m (%s)\x1b[0m", swScriptUrl);
        },
        onNeedRefresh() {
            console.log("\x1b[34m[SW]\x1b[32m Service Worker Update Available\x1b[0m");
        },
        onOfflineReady() {
            console.log("\x1b[34m[SW]\x1b[32m Service Worker Offline Ready\x1b[0m");
        },
    },
    render() {
        return null;
    },
    mounted() {
        const { offlineReady, needRefresh, updateServiceWorker } = useRegisterSW({
            immediate: true,
            onRegisteredSW: this.onRegisteredSW,
            onNeedRefresh: this.onNeedRefresh,
            onOfflineReady: this.onOfflineReady,
        });

        this.offlineReady = offlineReady.value;
        this.needRefresh = needRefresh.value;
    },
    watch: {
        offlineReady: {
            immediate: false,
            handler(offlineReady) {
                console.log("\x1b[34m[SW]\x1b[32m Service Worker Offline Ready\x1b[0m", offlineReady);
            },
        },
        needRefresh: {
            immediate: false,
            handler(needRefresh) {
                console.log("\x1b[34m[SW]\x1b[32m Service Worker Update Available\x1b[0m", needRefresh);
            },
        },
    },
});
</script>
