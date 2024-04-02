import type { App } from "vue";
import type { CustomTourGuideOptions } from "@/plugins/tours";
import type { TourGuideCallbacks } from ".";
import { TourGuideStep } from "@sjmc11/tourguidejs/src/types/TourGuideStep";

const steps = (__: (key: string) => string): TourGuideStep[] => [
    {
        title: __("Welcome to Wizarr"),
        content: __("We want to help you get started with Wizarr as quickly as possible. Consider following this tour to get a quick overview."),
    },
    {
        title: __("Dashboard Widgets"),
        content: __("These are your widgets. You can use them to get a quick overview of your Wizarr instance."),
        target: ".grid-stack-item:nth-child(2)",
    },
    {
        title: __("Latest Information"),
        content: __("Like this widget, it shows you the latest information about Wizarr and will be updated regularly by our amazing team."),
        target: ".latest-info",
    },
    {
        title: __("Edit Dashboard"),
        content: __("You can also edit your dashboard, delete widgets, add new widgets, and move them around."),
        target: "#editDashboard",
    },
];

const options = (__: (key: string) => string, app?: App): Partial<CustomTourGuideOptions> => {
    return {
        finishLabel: __("Next Page"),
    };
};

const callbacks = (__: (key: string) => string, app?: App): TourGuideCallbacks => {
    return {
        onFinish: () => {
            app?.config.globalProperties.$router.push("/admin/invitations");
        },
    };
};

export { steps, options, callbacks };
