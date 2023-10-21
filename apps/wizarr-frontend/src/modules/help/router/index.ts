import openServer from '@/router/middleware/openServer';
import type { RouteRecordRaw } from 'vue-router';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/help',
        name: 'help',
        component: () => import('../views/Help.vue'),
    },
    {
        path: '/open',
        name: 'open',
        component: () => '',
        meta: {
            middleware: [openServer],
        },
    },
];

export default routes;
