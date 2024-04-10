import type { CustomTourGuideStep, TourGuideCallbacks } from ".";

import type { App } from "vue";
import type TourGuideOptions from "@sjmc11/tourguidejs/src/core/options";

const steps = (__: (key: string) => string): CustomTourGuideStep[] => [
    {
        title: __("Your Users"),
        content: __("All of your media server users will appear here in a list. You can manage, edit, and delete them. Other information, like their expiration or creation date, will also be displayed here."),
        target: document.querySelector("#userList > li:nth-child(1)") ?? "#userList",
    },
    {
        title: __("Scan for Users"),
        content: __("Wizarr will automatically scan your media server for new users, but you can also manually scan for new users by clicking on the 'Scan for Users' button. This is useful if Wizarr has not gotten around to doing it yet."),
        target: "#scanUsers",
    },
];

const options = (__: (key: string) => string, app?: App): Partial<TourGuideOptions> => {
    return {
        finishLabel: __("Next Page"),
    };
};

const callbacks = (__: (key: string) => string, app?: App): TourGuideCallbacks => {
    return {
        onFinish: () => {
            app?.config.globalProperties.$router.push("/admin/settings");
        },
    };
};

export { steps, options, callbacks };
