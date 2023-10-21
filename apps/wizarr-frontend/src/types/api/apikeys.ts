export type APIKeys = APIKey[];

export interface APIKey {
    created: string;
    id: number;
    jti: string;
    key: string;
    name: string;
    user: number;
}
