import type { App } from 'vue';
import RocketChat from '@/ts/utils/rocketChat';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $RocketChat: typeof RocketChat;
    }
}

const vuePluginRocketChat = {
    install: (app: App) => {
        app.config.globalProperties.$RocketChat = RocketChat;
    },
};

export default vuePluginRocketChat;
