export type Requests = Request[];

export interface Request {
    id?: number;
    api_key: string;
    name: string;
    server_id?: string;
    service: string;
    url: string;
    created?: string;
}
