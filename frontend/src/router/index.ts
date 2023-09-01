import { createMemoryHistory, createRouter, createWebHistory } from "vue-router";
import { useProgressStore } from "@/stores/progress";
import { useUserStore } from "@/stores/user";
import { pinia } from "@/main";

import axios from "@/assets/ts/utils/Axios";

// Publicly Accessible Views
import HomeView from "@/views/DefaultViews/HomeView.vue";
import LoginView from "@/views/LoginViews/LoginView.vue";

// Semi Publicly Accessible Views
import SetupView from "@/views/SetupViews/SetupView.vue";

// Admin Accessible Views
import AdminView from "@/views/AdminViews/AdminView.vue";
import InviteView from "@/views/AdminViews/InviteView.vue";
import InvitationsView from "@/views/AdminViews/InvitationsView.vue";
import UsersView from "@/views/AdminViews/UsersView.vue";
import FlowEdtior from "@/views/AdminViews/FlowEditor.vue";

// Settings Views
import SettingsView from "@/views/SettingsViews/SettingsView.vue";
import DefaultView from "@/views/SettingsViews/DefaultView.vue";
import TasksView from "@/views/SettingsViews/TasksView.vue";
import AboutView from "@/views/SettingsViews/AboutView.vue";
import MediaView from "@/views/SettingsViews/MediaView.vue";

// Error Views
import NotFoundView from "@/views/DefaultViews/NotFoundView.vue";

const history = typeof window !== "undefined" ? createWebHistory() : createMemoryHistory();

const router = createRouter({
    history: history,
    routes: [
        {
            path: "/",
            name: "home",
            component: HomeView,
        },
        {
            path: "/login",
            name: "login",
            component: LoginView,
            meta: { requiresLoggedOut: true },
        },
        {
            path: "/setup/:step",
            alias: "/setup",
            name: "setup",
            component: SetupView,
        },
        {
            path: "/admin",
            name: "admin",
            redirect: { name: "admin-invite" },
            component: AdminView,
            meta: { requiresAuth: true },
            children: [
                {
                    path: "invite",
                    alias: "",
                    name: "admin-invite",
                    component: InviteView,
                },
                {
                    path: "invitations",
                    name: "admin-invitations",
                    component: InvitationsView,
                },
                {
                    path: "users",
                    name: "admin-users",
                    component: UsersView,
                },
                {
                    path: "flow-editor",
                    name: "admin-flow-editor",
                    component: FlowEdtior,
                },
                {
                    path: "settings",
                    name: "admin-settings",
                    component: SettingsView,
                    children: [
                        {
                            path: "",
                            name: "admin-settings",
                            component: DefaultView,
                            meta: { searchBar: true },
                        },
                        {
                            path: "media",
                            name: "admin-settings-media",
                            component: MediaView,
                            meta: { header: "Manage Media", subheader: "Configure server media" },
                        },
                        {
                            path: "tasks",
                            name: "admin-settings-tasks",
                            component: TasksView,
                            meta: { header: "Manage Tasks", subheader: "Configure server tasks" },
                        },
                        {
                            path: "about",
                            name: "admin-settings-about",
                            component: AboutView,
                            meta: { header: "About", subheader: "View server information" },
                        },
                    ],
                },
            ],
        },
        {
            path: "/:pathMatch(.*)*",
            name: "not-found",
            component: NotFoundView,
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
