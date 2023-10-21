import type { RouteRecordRaw } from 'vue-router';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/j/:invite',
        name: 'join-invite',
        component: () => import('../views/Join.vue'),
    },
    {
        path: '/join',
        name: 'join',
        component: () => import('../views/Join.vue'),
    },
];

export default routes;
