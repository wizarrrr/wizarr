import type { CustomTourGuideStep, TourGuideCallbacks } from ".";

import type { App } from "vue";

const steps = (__: (key: string) => string): CustomTourGuideStep[] => [
    {
        title: __("Your Settings"),
        content: __("All of your media server settings will appear here. We know you're going to spend a lot of time here 😝"),
    },
    {
        title: __("Search Settings"),
        content: __("Since there are a lot of settings, you can search for them by using the search bar."),
        target: "#searchSettings",
    },
    {
        title: __("Settings Categories"),
        content: __("We have categorized all of your settings to make it easier to find them."),
        target: "#settingsContainer1",
    },
    {
        title: __("End of Tour"),
        content: __("This is the end of the tour. We hope you enjoyed and found it informative! Please feel free to contact us on Discord and let us know what you think of Wizarr."),
    },
];

const callbacks = (__: (key: string) => string, app?: App): TourGuideCallbacks => {
    return {
        onFinish: () => {
            app?.config.globalProperties.$toast.info("Thanks for taking the tour!");
        },
    };
};

export { steps, callbacks };
