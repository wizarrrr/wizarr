import type { RouteRecordRaw } from 'vue-router';
import children from './children';
import requireAuth from '@/router/middleware/requireAuth';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/admin/settings',
        name: 'admin-settings',
        component: () => import('../views/Settings.vue'),
        meta: {
            middleware: [requireAuth],
        },
        children: children,
    },
];

export default routes;
