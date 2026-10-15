"""LDAP search filters that Wizarr builds from the admin settings."""

from ldap3.core.exceptions import LDAPException
from ldap3.operation.search import parse_filter


def is_valid_filter(search_filter: str) -> bool:
    """Return True when ldap3 can parse the filter."""
    try:
        parse_filter(
            search_filter.strip(),
            None,
            auto_escape=True,
            auto_encode=True,
            validator=None,
            check_names=False,
        )
    except LDAPException:
        return False
    return True


def build_sync_filter(object_class: str, sync_filter: str | None) -> str:
    """Return the filter that selects the users that the user sync imports.

    The object class filter always applies. The optional sync filter can only
    remove users from that set. Login does not use this filter.
    """
    base = f"(objectClass={object_class})"
    extra = (sync_filter or "").strip()
    return f"(&{base}{extra})" if extra else base
