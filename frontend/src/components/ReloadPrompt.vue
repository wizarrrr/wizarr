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
            console.log("Registered SW");
        },
        onNeedRefresh() {
            console.log("Need refresh");
        },
        onOfflineReady() {
            console.log("Offline ready");
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

        console.log(this.pwaInfo);
    },
    watch: {
        offlineReady: {
            immediate: false,
            handler(offlineReady) {
                console.log("Offline ready changed", offlineReady);
            },
        },
        needRefresh: {
            immediate: false,
            handler(needRefresh) {
                console.log("Need refresh changed", needRefresh);
            },
        },
    },
});
</script>
