import type { NavigationGuardNext } from "vue-router";
import { useServerStore } from "@/stores/server";

export default async function openServer({ next, authStore }: { next: NavigationGuardNext; authStore: any }) {
    try {
        const serverStore = useServerStore();
        location.href = serverStore.settings.server_url_override ?? serverStore.settings.server_url;
    } catch {
        console.error("Failed to open server");
    }

    return next();
}
