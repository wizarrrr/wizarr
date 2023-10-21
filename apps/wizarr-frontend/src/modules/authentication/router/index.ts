import type { RouteRecordRaw } from 'vue-router';
import requireNoAuth from '@/router/middleware/requireNoAuth';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/login',
        name: 'login',
        component: () => import('../views/LoginView.vue'),
        meta: {
            middleware: [requireNoAuth],
        },
    },
];

export default routes;
