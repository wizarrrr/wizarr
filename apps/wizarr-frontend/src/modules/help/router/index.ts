import type { RouteRecordRaw } from 'vue-router';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/help',
        name: 'help',
        component: () => import('../views/Help.vue'),
    }
];

export default routes;
