export type Sessions = Session[];

export interface Session {
    created: string;
    expires: string;
    id: number;
    ip: string;
    mfa_id?: string;
    revoked: boolean;
    session: string;
    user: number;
    user_agent: string;
}
