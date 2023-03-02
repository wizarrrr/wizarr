from app import Invitations



def isInviteValid(code):
        invitation = Invitations.get_or_none(Invitations.code == code)
        if not invitation:
            return False, "Invalid code"
        if invitation.expires and invitation.expires <= datetime.datetime.now():
            return False, "Invitation has expired."
        if invitation.used == True and invitation.unlimited != True:
            return False, "Invitation has already been used."
        return True, "okay"
