import type { RouteRecordRaw } from "vue-router";

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: "/request",
        name: "request",
        component: () => import("../views/Request.vue"),
    },
];

export default routes;
