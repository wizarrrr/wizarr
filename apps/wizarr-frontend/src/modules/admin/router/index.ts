import requireAuth from '@/router/middleware/requireAuth';
import children from './children';
import type { RouteRecordRaw } from 'vue-router';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/admin',
        name: 'admin',
        redirect: { name: 'admin-home' },
        component: () => import('../views/Admin.vue'),
        meta: {
            middleware: [requireAuth],
        },
        children: children,
    },
];

export default routes;
