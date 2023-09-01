export interface AuthenticatorRegistrationResponse {
    attestation: string;
    authenticator_selection: AuthenticatorSelection;
    challenge: string;
    exclude_credentials: ExcludeCredential[];
    pub_key_cred_params: PubKeyCredParam[];
    rp: Rp;
    timeout: number;
    user: User;
}

export interface AuthenticatorSelection {
    authenticator_attachment: string;
    require_resident_key: boolean;
    resident_key: string;
    user_verification: string;
}

export interface ExcludeCredential {
    id: string;
    transports: null;
    type: string;
}

export interface PubKeyCredParam {
    alg: number;
    type: string;
}

export interface Rp {
    id: string;
    name: string;
}

export interface User {
    display_name: string;
    id: string;
    name: string;
}