import type { RouteRecordRaw } from "vue-router";

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: "/setup",
        redirect: "/setup/welcome",
    },
    {
        path: "/setup/:step",
        name: "setup",
        component: () => import("@/views/SetupViews/SetupView.vue"),
    },
];

export default routes;
