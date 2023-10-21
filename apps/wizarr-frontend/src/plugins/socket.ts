import SocketIO, { type Socket, type ManagerOptions } from 'socket.io-client';
import type {
    ReservedOrUserListener,
    ReservedOrUserEventNames,
    EventsMap,
} from '@socket.io/component-emitter';
import type { App } from 'vue';
import type { SocketOptions } from 'dgram';
import type { PiniaPluginContext } from 'pinia';

export interface ServerToClientEvents {
    [event: string]: (...args: any[]) => void;
}

export interface ClientToServerEvents {
    [event: string]: (...args: any[]) => void;
}

declare module 'pinia' {
    export interface PiniaCustomProperties {
        $socket: Socket<ServerToClientEvents, ClientToServerEvents>;
        $io: typeof SocketIO;
        sockets: {
            subscribe<
                Ev extends ReservedOrUserEventNames<EventsMap, EventsMap>,
            >(
                eventName: Ev,
                handler: ReservedOrUserListener<EventsMap, EventsMap, Ev>,
            ): void;
            unsubscribe<
                Ev extends ReservedOrUserEventNames<EventsMap, EventsMap>,
            >(
                eventName: Ev,
            ): void;
        };
    }
}

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $socket: Socket<ServerToClientEvents, ClientToServerEvents>;
        $io: typeof SocketIO;
        sockets: {
            subscribe<
                Ev extends ReservedOrUserEventNames<EventsMap, EventsMap>,
            >(
                eventName: Ev,
                handler: ReservedOrUserListener<EventsMap, EventsMap, Ev>,
            ): void;
            unsubscribe<
                Ev extends ReservedOrUserEventNames<EventsMap, EventsMap>,
            >(
                eventName: Ev,
            ): void;
        };
    }
}

const useSocketIO = (
    uri?: string,
    opts?: Partial<ManagerOptions & SocketOptions>,
) => {
    const optional_uri =
        uri ?? localStorage.getItem('base_url') ?? window.location.origin;
    const socket = SocketIO(optional_uri, opts);
    return socket as Socket<ServerToClientEvents, ClientToServerEvents>;
};

const piniaPluginSocketIO = (context: PiniaPluginContext) => {
    context.store.$socket = context.app.config.globalProperties.$socket;
    context.store.sockets = context.app.config.globalProperties.sockets;
};

const vuePluginSocketIO = {
    install: (
        app: App,
        options: {
            uri?: string;
            opts?: Partial<ManagerOptions & SocketOptions>;
        },
    ) => {
        // const uri = options.uri ?? localStorage.getItem("base_url") ?? window.location.origin;
        // app.config.globalProperties.$socket = SocketIO(uri, options.opts);
        app.config.globalProperties.$io = SocketIO;
        // app.config.globalProperties.sockets = {
        //     subscribe<Ev extends ReservedOrUserEventNames<EventsMap, EventsMap>>(eventName: Ev, handler: ReservedOrUserListener<EventsMap, EventsMap, Ev>) {
        //         socket.on(eventName, handler);
        //     },
        //     unsubscribe<Ev extends ReservedOrUserEventNames<EventsMap, EventsMap>>(eventName: Ev) {
        //         socket.off(eventName);
        //     },
        // };
    },
};

export default vuePluginSocketIO;
export { useSocketIO, piniaPluginSocketIO, vuePluginSocketIO };
