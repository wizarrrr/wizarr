import type { RouteRecordRaw } from 'vue-router';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/setup',
        name: 'setup',
        component: () => import('../views/Setup.vue'),
    },
];

export default routes;
