import Auth from '@/api/authentication';

import { useRouter } from 'vue-router';
import type { NavigationGuardNext } from 'vue-router';

const router = useRouter();

export default async function requireAuth({
    next,
    authStore,
}: {
    next: NavigationGuardNext;
    authStore: any;
}) {
    try {
        const auth = new Auth();
        if (!(await auth.isAuthenticated())) return router.push('/login');
    } catch (error) {
        console.error(error);
        return next({ name: 'login' });
    }

    return next();
}
