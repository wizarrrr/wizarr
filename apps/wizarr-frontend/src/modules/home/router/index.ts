import type { RouteRecordRaw } from 'vue-router';

const routes: Readonly<RouteRecordRaw[]> = [
    {
        path: '/i/:invite',
        name: 'invite',
        component: () => import('../views/Home.vue'),
    },
    {
        path: '/',
        name: 'home',
        component: () => import('../views/Home.vue'),
    },
    // TODO: Remove this route after a few versions to allow users to get used to the new route
    {
        path: '/j/:invite',
        name: 'deprecated-invite',
        component: () => import('../views/Home.vue'),
    },
    {
        path: '/join',
        name: 'deprecated-join',
        component: () => import('../views/Home.vue'),
    },
];

export default routes;
