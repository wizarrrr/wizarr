export interface LocalUser {
    id: number;
    displayName: string;
    username: string;
    email: string;
    avatar: string;
    role: string;
    created: string;
    lastLogin: string;
}

export interface APIUser {
    id: number;
    display_name: string;
    username: string;
    email: string;
    avatar: string;
    role: string;
    created: string;
    last_login: string;
}
