export interface Server {
    settings: ServerSettings;
    version: string;
    update_available: boolean;
    debug: boolean;
    setup_required: boolean;
}

export interface ServerSettings {
    server_name: string;
    server_url: string;
    server_url_override?: string;
    server_type: "jellyfin" | "plex" | "emby";
    server_verified: string;
    server_discord_id?: string;
    bug_reporting?: boolean | string;
}
