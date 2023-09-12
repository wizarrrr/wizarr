import { useServerStore } from "@/stores/server";
import type { NavigationGuardNext } from "vue-router";

export default async function openServer({ next, authStore }: { next: NavigationGuardNext; authStore: any }) {
    try {
        const serverStore = useServerStore();
        window.open(serverStore.settings.server_url, "_blank");
    } catch {}

    return next();
}
