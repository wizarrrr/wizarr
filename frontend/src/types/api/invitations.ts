export type Invitations = Invitation[];

export interface Invitation {
    code: string;
    created: string;
    duration: any;
    expires: string;
    id: number;
    plex_allow_sync: boolean;
    plex_home: boolean;
    specific_libraries: string;
    unlimited: boolean;
    used: boolean;
    used_at: any;
    used_by: Array<number>;
}
