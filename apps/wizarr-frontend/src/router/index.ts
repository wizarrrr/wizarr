import {
    createMemoryHistory,
    createRouter,
    createWebHistory,
} from 'vue-router';
import { useProgressStore } from '@/stores/progress';
import { useAuthStore } from '@/stores/auth';

// Import the middleware pipeline
import middlewarePipeline from './middlewarePipeline';

// Import all Routes from the modules
import homeRoutes from '@/modules/home/router';
import authenticationRoutes from '@/modules/authentication/router';
import adminRoutes from '@/modules/admin/router';
import settingsRoutes from '@/modules/settings/router';
import helpRoutes from '@/modules/help/router';
import requestRoutes from '@/modules/requests/router';
import setupRoutes from '@/modules/setup/router';
import coreRoutes from '@/modules/core/router';

const router = createRouter({
    history:
        typeof window !== 'undefined'
            ? createWebHistory()
            : createMemoryHistory(),
    routes: [
        ...homeRoutes, // Homepage routes ["/", "/i/:invite"]
        ...authenticationRoutes, // Authentication routes ["/login", "/register", "/forgot-password", "/reset-password"]
        ...adminRoutes, // Admin routes ["/admin", "/admin/:page"]
        ...settingsRoutes, // Settings routes ["/admin/settings", "/admin/settings/:page"]
        ...helpRoutes, // Help routes ["/help", "/open"]
        ...requestRoutes, // Request routes ["/request"]
        ...setupRoutes, // Setup routes ["/setup", "/setup/:step"]
        ...coreRoutes, // Core routes ["/:pathMatch(.*)*"]
    ],
});

router.beforeEach(async (to, from, next) => {
    // Get the auth store and check if the user is authenticated
    const authStore = useAuthStore();

    // Start progress bar
    useProgressStore().startProgress();

    // Check if there exists a middleware to run
    if (!to.meta.middleware) {
        return next();
    }

    // Determine the middleware pipeline as an array and create a context object
    const middleware = to.meta.middleware as any[];
    const context = { to, from, next, authStore };

    // Run the middleware pipeline
    return middleware[0]({
        ...context,
        next: middlewarePipeline(context, middleware, 1),
    });
});

router.afterEach(() => {
    // Stop progress bar
    useProgressStore().startProgress();
});

export default router;
export { router };
