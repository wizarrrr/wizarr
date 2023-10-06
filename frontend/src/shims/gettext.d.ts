export {};
declare module "vue" {
    interface ComponentCustomProperties {
        __: (
            msgid: string,
            parameters?: {
                [key: string]: string;
            },
            disableHtmlEscaping?: boolean,
        ) => string;
        _x: (
            context: string,
            msgid: string,
            parameters?: {
                [key: string]: string;
            },
            disableHtmlEscaping?: boolean,
        ) => string;
        _n: (
            msgid: string,
            plural: string,
            n: number,
            parameters?: {
                [key: string]: string;
            },
            disableHtmlEscaping?: boolean,
        ) => string;
        _xn: (
            context: string,
            msgid: string,
            plural: string,
            n: number,
            parameters?: {
                [key: string]: string;
            },
            disableHtmlEscaping?: boolean,
        ) => string;
    }
}
