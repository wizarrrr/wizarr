import type { VitePWAOptions } from "vite-plugin-pwa";

const VitePWAConfig: Partial<VitePWAOptions> = {
    registerType: "autoUpdate",
    devOptions: {
        enabled: false,
    },
};

export default VitePWAConfig;
