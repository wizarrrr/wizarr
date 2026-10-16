"""Access rules for the public wizard pages."""

from dataclasses import dataclass

from app.models import MediaServer, Settings


@dataclass(frozen=True)
class WizardGuide:
    """A link to the wizard steps of one server type."""

    server_name: str
    server_type: str


def wizard_acl_enabled() -> bool:
    """Return True if the "Protect Wizard Access" setting is on.

    The setting is on by default. Then only admins and invited users can
    open the wizard steps (#611).
    """
    row = Settings.query.filter_by(key="wizard_acl_enabled").first()
    if row is None or row.value is None:
        return True
    return str(row.value).lower() != "false"


def public_wizard_guides() -> list[WizardGuide]:
    """Return one wizard guide for each server type, if the wizard is public.

    When "Protect Wizard Access" is on, the wizard steps are only for
    invited users. Then this function returns no guides.
    """
    if wizard_acl_enabled():
        return []

    guides: dict[str, WizardGuide] = {}
    for server in MediaServer.query.order_by(MediaServer.id).all():
        guides.setdefault(
            server.server_type,
            WizardGuide(server.name or server.server_type, server.server_type),
        )
    return list(guides.values())
