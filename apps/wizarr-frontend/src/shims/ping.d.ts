declare module 'ping.js' {
    export type CallbackFunc = (err: boolean, ping: number) => void;
    export type PingFunc = (source: string, cb?: CallbackFunc) => Promise<any>;
    export default class Ping {
        ping: PingFunc;
    }
}
