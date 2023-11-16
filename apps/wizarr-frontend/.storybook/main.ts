import type { StorybookConfig } from "@storybook/vue3-vite";

const config: StorybookConfig = {
    stories: [
        "../src/**/*.mdx", // MDX stories
        "../src/**/*.stories.@(js|jsx|ts|tsx|mdx)", // JS/TS stories
    ],
    addons: ["@storybook/addon-essentials", "@storybook/addon-interactions", "@storybook/addon-docs"],
    framework: {
        name: "@storybook/vue3-vite",
        options: {
            builder: {
                viteConfigPath: "apps/wizarr-frontend/vite.config.ts",
            },
        },
    },
    docs: {
        autodocs: "tag",
        defaultName: "Documentation",
    },
    core: {
        disableTelemetry: true,
        disableWhatsNewNotifications: true,
        enableCrashReports: false,
    },
};

export default config;

// To customize your Vite configuration you can use the viteFinal field.
// Check https://storybook.js.org/docs/react/builders/vite#configuration
// and https://nx.dev/recipes/storybook/custom-builder-configs
