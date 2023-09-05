export type MFAList = MFA[];

export interface MFA {
    attestation: string;
    created: string;
    credential_id: string;
    id: number | string;
    name: string;
    public_key: string;
    sign_count: number;
    transports: string;
    user_id: string;
}
