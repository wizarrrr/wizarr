# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

from uuid import UUID
from datetime import datetime


class Configuration:
    audio_language_preference: str
    play_default_audio_track: bool
    subtitle_language_preference: str
    display_missing_episodes: bool
    grouped_folders: list[str]
    subtitle_mode: str
    display_collections_view: bool
    enable_local_password: bool
    ordered_views: list[str]
    latest_items_excludes: list[str]
    my_media_excludes: list[str]
    hide_played_in_latest: bool
    remember_audio_selections: bool
    remember_subtitle_selections: bool
    enable_next_episode_auto_play: bool

class AccessSchedule:
    id: int
    user_id: UUID
    day_of_week: str
    start_hour: int
    end_hour: int


class Policy:
    is_administrator: bool
    is_hidden: bool
    is_disabled: bool
    max_parental_rating: int
    blocked_tags: list[str]
    enable_user_preference_access: bool
    access_schedules: list[AccessSchedule]
    block_unrated_items: list[str]
    enable_remote_control_of_other_users: bool
    enable_shared_device_control: bool
    enable_remote_access: bool
    enable_live_tv_management: bool
    enable_live_tv_access: bool
    enable_media_playback: bool
    enable_audio_playback_transcoding: bool
    enable_video_playback_transcoding: bool
    enable_playback_remuxing: bool
    force_remote_source_transcoding: bool
    enable_content_deletion: bool
    enable_content_deletion_from_folders: list[str]
    enable_content_downloading: bool
    enable_sync_transcoding: bool
    enable_media_conversion: bool
    enabled_devices: list[str]
    enable_all_devices: bool
    enabled_channels: list[UUID]
    enable_all_channels: bool
    enabled_folders: list[UUID]
    enable_all_folders: bool
    invalid_login_attempt_count: int
    login_attempts_before_lockout: int
    max_active_sessions: int
    enable_public_sharing: bool
    blocked_media_folders: list[UUID]
    blocked_channels: list[UUID]
    remote_client_bitrate_limit: int
    authentication_provider_id: str
    password_reset_provider_id: str
    sync_play_access: str


class EmbyUser:
    name: str
    server_id: str
    server_name: str
    id: UUID
    primary_image_tag: str
    has_password: bool
    has_configured_password: bool
    has_configured_easy_password: bool
    enable_auto_login: bool
    last_login_date: datetime
    last_activity_date: datetime
    configuration: Configuration
    policy: Policy
    primary_image_aspect_ratio: int
