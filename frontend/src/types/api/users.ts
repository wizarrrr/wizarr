export type Users = User[];

export interface User {
    auth: string | null;
    code: string | null;
    created: string;
    email: string;
    expires: string | null;
    id: number;
    token: string;
    username: string;
}
