export type Invitations = Invitation[];

export interface Invitation {
    code: string;
    created: string;
    duration: any;
    expires: string;
    id: number;
    plex_allow_sync: boolean;
    live_tv: boolean;
    hide_user: boolean;
    allow_download: boolean;
    sessions: number;
    specific_libraries: string;
    unlimited: boolean;
    used: boolean;
    used_at: any;
    used_by: Array<number>;
}
