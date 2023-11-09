import type { RouteRecordName, Router } from "vue-router";

import type { App } from "vue";
import type { CustomTourGuideOptions } from "@/plugins/tours";
import type { Language } from "vue3-gettext";
import { TourGuideClient } from "@sjmc11/tourguidejs/src/Tour";
import type TourGuideOptions from "@sjmc11/tourguidejs/src/core/options";
import type { TourGuideStep } from "@sjmc11/tourguidejs/src/types/TourGuideStep";
import defaultOptions from "@sjmc11/tourguidejs/src/util/util_default_options";
import { useUserStore } from "@/stores/user";

export interface CustomTourGuideStep extends TourGuideStep {
    onBackdropClick?: () => void | Promise<void>;
    onBeforeEnter?: () => void | Promise<void>;
}

export type TourGuideCallbacks = {
    onFinish?: () => void | Promise<void>;
    onAfterExit?: () => void | Promise<void>;
    onAfterStepChange?: () => void | Promise<void>;
    onBeforeExit?: () => void | Promise<void>;
    onBeforeStepChange?: () => void | Promise<void>;
};

export type TourGuideStepsReturn = {
    steps: TourGuideStep[];
    options?: Partial<CustomTourGuideOptions>;
    callbacks?: TourGuideCallbacks;
};

export type TourGuideImport = {
    steps: (__: (key: string) => string) => TourGuideStep[];
    options?: (__: (key: string) => string, app?: App) => Partial<TourGuideOptions>;
    callbacks?: (__: (key: string) => string, app?: App) => TourGuideCallbacks;
};

/**
 * checkTourAvailability
 * Check if tour is available
 * @param tour
 * @returns boolean
 */
export const checkTourAvailability = (tour: string): boolean => {
    // Get an array of tour files from the tours folder
    const tours = import.meta.glob("../tours/*.ts");

    // Extract the tour name from the file paths in tours (./*.ts)
    const tourNames = Object.keys(tours).map((tour) => RegExp(/\.\/(.*).ts/).exec(tour.replace("../tours/", ""))![1]);

    // Check if the tour exists
    return tourNames.includes(tour);
};

/**
 * loadRouteTour
 * Load tour when route is loaded
 * @param route
 * @param options
 * @returns
 */
const loadRouterTour = (router: Router, options: CustomTourGuideOptions) => {
    // Initialize the tour guide
    const tourGuide = new TourGuideClient({
        ...options,
        debug: process.env.NODE_ENV === "development",
    });

    // Load the tour when the route is loaded
    router.afterEach(async (to) => {
        const userStore = useUserStore(options.app.config.globalProperties.$pinia);
        if (!userStore.user?.tutorial && checkTourAvailability(to.name as string)) {
            await loadTour(to.name as RouteRecordName, tourGuide, {
                ...options,
                userStore: userStore,
            });
        }
    });
};

/**
 * defaultOnFinish
 * Default on finish callback
 * @param tourGuide
 * @param options
 * @param callback
 * @returns
 */
const defaultOnFinish = async (tourGuide: TourGuideClient, options?: CustomTourGuideOptions, callback?: () => void | Promise<void>) => {
    // Reset the tour guide options
    tourGuide.options = { ...defaultOptions, ...options };

    // Call the callback if it exists
    await callback?.();
};

/**
 * defaultOnBeforeStepChange
 * Default on before step change callback
 * @param tourGuide
 * @param callback
 * @returns
 */
const defaultOnBeforeStepChange = async (tourGuide: TourGuideClient, callback?: () => void | Promise<void>) => {
    // Get the current step
    const currentStep = tourGuide.tourSteps[tourGuide.activeStep + 1] as CustomTourGuideStep;

    // Call the current step's onBeforeEnter callback if it exists
    await currentStep?.onBeforeEnter?.();

    // Call the callback if it exists
    await callback?.();
};

/**
 * defaultOnAfterExit
 * Default on after exit callback
 * @param tourGuide
 * @param callback
 * @returns
 */
const defaultOnAfterExit = async (tourGuide: TourGuideClient, options?: CustomTourGuideOptions, callback?: () => void | Promise<void>) => {
    // Don't show the tour guide again if the tour has been completed
    const axios = options?.app.config.globalProperties.$axios;

    // Update the user in the database
    await axios!.patch("/api/accounts/me", { tutorial: true }).then((response) => {
        options?.userStore?.$patch({ user: { ...response.data } });
    });

    // Call the callback if it exists
    await callback?.();
};

/**
 * loadTour
 * Load tour using route name
 * @param route
 * @param options
 * @returns
 */
const loadTour = async (name: RouteRecordName, tourGuide: TourGuideClient, options?: CustomTourGuideOptions) => {
    // Make sure the tour name is a string
    const tourName = name.toString();

    // Don't load the tour if the tour guide is visible
    if (tourGuide.isVisible) {
        if (tourGuide.group !== tourName) {
            tourGuide.exit();
        }
        return;
    }

    // Get the tour
    const tour = await getTourSteps(tourName, options?.i18n, options?.app).catch((error) => {
        console.log(`Tour ${tourName} does not exist`);
    });

    // Verify the tour exists
    if (!tour) return;

    // Add the steps to the tour guide if they don't exist
    tourGuide.addSteps(tour.steps.map((step) => ({ ...step, group: tourName })).filter((step) => !tourGuide.tourSteps.map((step) => step.content).includes(step.content)));

    // Add the options to the tour guide if they exist
    tourGuide.options = { ...tourGuide.options, ...tour.options };

    const onFinishCallback = async () => await defaultOnFinish(tourGuide, options, tour.callbacks?.onFinish);
    const onBeforeStepChangeCallback = async () => await defaultOnBeforeStepChange(tourGuide, tour.callbacks?.onBeforeStepChange);
    const onAfterExitCallback = async () => await defaultOnAfterExit(tourGuide, options, tour.callbacks?.onAfterExit);

    // Add the callbacks to the tour guide if they exist
    tourGuide.onFinish(onFinishCallback);
    tourGuide.onAfterExit(onAfterExitCallback);
    tour.callbacks?.onAfterStepChange && tourGuide.onAfterStepChange(tour.callbacks.onAfterStepChange);
    tour.callbacks?.onBeforeExit && tourGuide.onBeforeExit(tour.callbacks.onBeforeExit);
    tourGuide.onBeforeStepChange(onBeforeStepChangeCallback);

    // Start the tour
    tourGuide.start(tourName);
};

/**
 * getTour
 * Get tour using route name
 * @param tour
 * @returns
 */
const getTourSteps = async (tour: string, i18n?: Language, app?: App): Promise<TourGuideStepsReturn> => {
    // Import the tour steps from the tours folder
    const { steps, options, callbacks } = (await import(`../tours/${tour}.ts`)) as TourGuideImport;

    // Verify the tour steps are valid
    if (!steps) throw new Error(`Tour steps for ${tour} do not exist`);

    // Translate the tour steps
    return {
        steps: steps(i18n?.$gettext ?? ((key) => key)),
        options: options ? options(i18n?.$gettext ?? ((key) => key), app) : undefined,
        callbacks: callbacks ? callbacks(i18n?.$gettext ?? ((key) => key), app) : undefined,
    };
};

export default loadRouterTour;
