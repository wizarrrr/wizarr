import type { CustomTourGuideStep, TourGuideCallbacks } from ".";

import type { App } from "vue";
import type TourGuideOptions from "@sjmc11/tourguidejs/src/core/options";

const steps = (__: (key: string) => string): CustomTourGuideStep[] => [
    {
        title: __("Your Invitations"),
        content: __("This is where you can manage your invitations. They will appear here in a list. Invitations are used to invite new users to your media server."),
        target: document.querySelector("#invitationList > li:nth-child(1)") ?? "#invitationList",
    },
    {
        title: __("Create Invitation"),
        content: __("You can create a new invitation by clicking on the 'Create Invitation' button."),
        target: "#createInvitation",
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
            app?.config.globalProperties.$router.push("/admin/users");
        },
    };
};

export { steps, options, callbacks };
