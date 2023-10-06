export type Webhooks = Webhook[];

export interface Webhook {
    created: string;
    id: number;
    name: string;
    url: string;
}
