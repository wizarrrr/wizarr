import { createMemoryHistory, createRouter, createWebHistory } from "vue-router";
import { useProgressStore } from "@/stores/progress";
import { useUserStore } from "@/stores/user";
import { pinia } from "@/main";

const router = createRouter({
    history: typeof window !== "undefined" ? createWebHistory() : createMemoryHistory(),
    routes: [
        {
            path: "/",
            name: "home",
            component: () => import("@/views/DefaultViews/HomeView.vue"),
        },
        {
            path: "/login",
            name: "login",
            component: () => import("@/views/LoginViews/LoginView.vue"),
            meta: { requiresLoggedOut: true },
        },
        {
            path: "/setup",
            redirect: { name: "setup" },
        },
        {
            path: "/setup/:step",
            name: "setup",
            component: () => import("@/views/SetupViews/SetupView.vue"),
        },
        {
            path: "/admin",
            name: "admin",
            redirect: { name: "admin-invite" },
            component: () => import("@/views/AdminViews/AdminView.vue"),
            meta: { requiresAuth: true },
            children: [
                {
                    path: "invite",
                    alias: "",
                    name: "admin-invite",
                    component: () => import("@/views/AdminViews/InviteView.vue"),
                },
                {
                    path: "invitations",
                    name: "admin-invitations",
                    component: () => import("@/views/AdminViews/InvitationsView.vue"),
                },
                {
                    path: "users",
                    name: "admin-users",
                    component: () => import("@/views/AdminViews/UsersView.vue"),
                },
                {
                    path: "flow-editor",
                    name: "admin-flow-editor",
                    component: () => import("@/views/AdminViews/FlowEditor.vue"),
                },
                {
                    path: "settings",
                    name: "admin-settings",
                    component: () => import("@/views/SettingsViews/SettingsView.vue"),
                    children: [
                        {
                            path: "",
                            name: "admin-settings",
                            component: () => import("@/views/SettingsViews/DefaultView.vue"),
                            meta: { searchBar: true },
                        },
                        {
                            path: "media",
                            name: "admin-settings-media",
                            component: () => import("@/views/SettingsViews/MediaView.vue"),
                            meta: { header: "Manage Media", subheader: "Configure server media" },
                        },
                        {
                            path: "mfa",
                            name: "admin-settings-mfa",
                            component: () => import("@/views/SettingsViews/MFAView.vue"),
                            meta: { header: "Manage MFA", subheader: "Configure multi-factor authentication" },
                        },
                        {
                            path: "tasks",
                            name: "admin-settings-tasks",
                            component: () => import("@/views/SettingsViews/TasksView.vue"),
                            meta: { header: "Manage Tasks", subheader: "Configure server tasks" },
                        },
                        {
                            path: "about",
                            name: "admin-settings-about",
                            component: () => import("@/views/SettingsViews/AboutView.vue"),
                            meta: { header: "About", subheader: "View server information" },
                        },
                    ],
                },
            ],
        },
        {
            path: "/:pathMatch(.*)*",
            name: "not-found",
            component: () => import("@/views/DefaultViews/NotFoundView.vue"),
        },
    ],
});

router.beforeEach((to, from, next) => {
    // Get user store and check if user is authenticated
    const userStore = useUserStore(pinia);
    const progressStore = useProgressStore(pinia);
    const isAuthenticated = userStore.isAuthenticated;

    // Start progress bar
    progressStore.startProgress();

    // Refresh token
    // isAuthenticated ? axios.get("/api/auth/refresh", { disableInfoToast: true }).catch(() => userStore.logout()) : null;

    // Check if route requires authentication or not
    const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
    const requiresLoggedOut = to.matched.some((record) => record.meta.requiresLoggedOut);

    if (requiresAuth && !isAuthenticated) next({ name: "login" });
    else if (requiresLoggedOut && isAuthenticated) next({ name: "admin" });

    next();
});

router.afterEach(() => {
    // Stop progress bar
    const progressStore = useProgressStore(pinia);
    progressStore.stopProgress();
});

export default router;
export { router };
