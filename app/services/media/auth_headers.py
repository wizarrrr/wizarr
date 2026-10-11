def media_browser_auth_headers(token: str | None) -> dict[str, str]:
    """Return Jellyfin/Emby auth headers accepted by modern and legacy servers."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f'MediaBrowser Token="{token}"'
        headers["X-Emby-Token"] = token
    return headers
