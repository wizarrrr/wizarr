"""Service for resolving server names for invitations.

This module handles the logic for determining what name to display in invitations,
falling back from global Display Name to actual server names when needed.
"""

from app.models import MediaServer, Settings


def resolve_invitation_server_name(servers: list[MediaServer]) -> str:
    """
    Resolve the server name to display for an invitation.

    Priority:
    1. Single server invitations: Always use the actual server name
    2. Multi-server invitations: Use global "Display Name" setting if set,
       otherwise comma-separated list of server names

    Args:
        servers: List of MediaServer instances associated with the invitation

    Returns:
        str: The resolved server name to display
    """
    # Handle edge case: no servers
    if not servers:
        return "Unknown Server"

    # Single server: ALWAYS use the actual server name
    if len(servers) == 1:
        return servers[0].name

    # Multiple servers: Check for global Display Name setting first
    display_name_setting = Settings.query.filter_by(key="server_name").first()

    if (
        display_name_setting
        and display_name_setting.value
        and display_name_setting.value.strip()
        and display_name_setting.value != "Wizarr"
    ):
        # Use global Display Name for multi-server invitations
        return display_name_setting.value

    # Fallback: comma-separated list of server names
    server_names = [server.name for server in servers]
    return ", ".join(server_names)


def get_server_names_for_api(servers: list[MediaServer]) -> list[str]:
    """
    Get a list of server names for API responses.

    Args:
        servers: List of MediaServer instances

    Returns:
        List[str]: List of server names
    """
    return [server.name for server in servers] if servers else []


def get_display_name_info(servers: list[MediaServer]) -> dict:
    """
    Get comprehensive display name information for API responses.

    Args:
        servers: List of MediaServer instances associated with the invitation

    Returns:
        dict: Information about display names including:
            - display_name: The resolved display name to show
            - server_names: List of individual server names
            - uses_global_setting: Whether global setting is being used
            - global_setting_value: Current global setting value
    """
    display_name_setting = Settings.query.filter_by(key="server_name").first()
    global_setting_value = display_name_setting.value if display_name_setting else None

    # Check if we're using the global setting
    uses_global_setting = bool(
        global_setting_value
        and global_setting_value.strip()
        and global_setting_value != "Wizarr"
    )

    # Get the resolved display name
    display_name = resolve_invitation_server_name(servers)

    # Get individual server names
    server_names = get_server_names_for_api(servers)

    return {
        "display_name": display_name,
        "server_names": server_names,
        "uses_global_setting": uses_global_setting,
        "global_setting_value": global_setting_value,
    }
