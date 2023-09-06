import { createMemoryHistory, createRouter, createWebHistory } from "vue-router";
import { useProgressStore } from "@/stores/progress";
import { useAuthStore } from "@/stores/auth";

import middlewarePipeline from "./middlewarePipeline";
import requireAuth from "./middleware/requireAuth";
import requireNoAuth from "./middleware/requireNoAuth";

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
            meta: {
                middleware: [requireNoAuth],
            },
        },
        {
            path: "/setup",
            redirect: "/setup/welcome",
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
            meta: {
                middleware: [requireAuth],
            },
            children: [
                {
                    path: "test",
                    name: "test",
                    component: () => import("@/views/TestView.vue"),
                },
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
                            path: "logs",
                            name: "admin-settings-logs",
                            component: () => import("@/views/SettingsViews/LogsView.vue"),
                            meta: { header: "View Logs", subheader: "View server logs" },
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

router.beforeEach(async (to, from, next) => {
    // Get the auth store and check if the user is authenticated
    const authStore = useAuthStore();

    // Start progress bar
    useProgressStore().startProgress();

    // Check if there exists a middleware to run
    if (!to.meta.middleware) {
        return next();
    }

    // Determine the middleware pipeline as an array and create a context object
    const middleware = to.meta.middleware as any[];
    const context = { to, from, next, authStore };

    // Run the middleware pipeline
    return middleware[0]({ ...context, next: middlewarePipeline(context, middleware, 1) });
});

router.afterEach(() => {
    // Stop progress bar
    useProgressStore().startProgress();
});

export default router;
export { router };
