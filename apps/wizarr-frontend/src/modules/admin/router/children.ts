import type { RouteRecordRaw } from 'vue-router';

const children: RouteRecordRaw[] = [
    {
        path: '',
        name: 'admin-home',
        component: () => import('../pages/Home.vue'),
    },
    {
        path: 'invitations',
        name: 'admin-invitations',
        component: () => import('../pages/Invitations.vue'),
    },
    {
        path: 'users',
        name: 'admin-users',
        component: () => import('../pages/Users.vue'),
    },
    {
        path: 'flow-editor',
        name: 'admin-flow-editor',
        component: () => import('../pages/FlowEditor.vue'),
    },
];

export default children;
