import Auth from '@/api/authentication';

import type { NavigationGuardNext } from 'vue-router';

export default async function requireAuth({
    next,
    authStore,
}: {
    next: NavigationGuardNext;
    authStore: any;
}) {
    try {
        const auth = new Auth();
        if (await auth.isAuthenticated()) return next({ name: 'admin' });
    } catch (error) {
        console.error(error);
        return next();
    }

    return next();
}
