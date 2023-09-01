from datetime import datetime

from app.models.database import Invitations
from app.exceptions import InvalidUsage


def is_invite_valid(code):
    invitation = Invitations.get_or_none(Invitations.code == code)

    if not invitation:
        return False, "Invalid code"

    if invitation.used is True and invitation.unlimited is not True:
        return False, "Invitation has already been used."

    if invitation.expires and invitation.expires <= datetime.now():
        return False, "Invitation has expired."

    return True, "okay"


def get_invitation(code) -> Invitations:
    invite = Invitations.get_or_none(Invitations.code == code)

    if not invite:
        raise InvalidUsage("Invalid code")

    return invite
