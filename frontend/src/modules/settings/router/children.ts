import type { RouteRecordRaw } from "vue-router";

const children: RouteRecordRaw[] = [
    {
        path: "",
        name: "admin-settings",
        component: () => import("../pages/Main.vue"),
        meta: { searchBar: true },
    },
    {
        path: "media",
        name: "admin-settings-media",
        component: () => import("../pages/Media.vue"),
        meta: { header: "Manage Media", subheader: "Configure media server" },
    },
    {
        path: "webhooks",
        name: "admin-settings-webhooks",
        component: () => import("../pages/Webhooks.vue"),
        meta: { header: "Manage Webhooks", subheader: "Configure webhooks" },
    },
    {
        path: "account",
        name: "admin-settings-account",
        component: () => import("../pages/Account.vue"),
        meta: { header: "Manage Account", subheader: "Configure your account" },
    },
    {
        path: "sessions",
        name: "admin-settings-sessions",
        component: () => import("../pages/Sessions.vue"),
        meta: { header: "Manage Sessions", subheader: "View and revoke your sessions" },
    },
    {
        path: "logs",
        name: "admin-settings-logs",
        component: () => import("../pages/Logs.vue"),
        meta: { header: "View Logs", subheader: "View server logs" },
    },
    {
        path: "mfa",
        name: "admin-settings-mfa",
        component: () => import("../pages/Passkeys.vue"),
        meta: { header: "Manage MFA", subheader: "Configure multi-factor authentication" },
    },
    {
        path: "tasks",
        name: "admin-settings-tasks",
        component: () => import("../pages/Tasks.vue"),
        meta: { header: "Manage Tasks", subheader: "Configure server tasks" },
    },
    {
        path: "backup",
        name: "admin-settings-backup",
        component: () => import("../pages/Backup.vue"),
        meta: { header: "Backup Server", subheader: "Backup server data" },
    },
    {
        path: "about",
        name: "admin-settings-about",
        component: () => import("../pages/About.vue"),
        meta: { header: "About", subheader: "View server information" },
    },
];

export default children;
