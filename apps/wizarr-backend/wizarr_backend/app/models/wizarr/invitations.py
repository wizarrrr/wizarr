from datetime import datetime, timedelta
from json import JSONDecodeError, loads, dumps
from secrets import token_hex

from playhouse.shortcuts import model_to_dict
from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import (BaseType, BooleanType, DateTimeType, IntType,
                              StringType)

from app.models.database.invitations import Invitations
from app.models.database.libraries import Libraries

# Custom specific_libraries type that converts a string to a list if needed
class SpecificLibrariesType(BaseType):
    """Specific Libraries Type"""

    def to_native(self, value, _):
        if isinstance(value, str):
            try:
                return loads(value)
            except JSONDecodeError as e:
                raise ValidationError("Invalid libraries") from e

        return value


class InvitationsModel(Model):
    """Invitations Model"""

    # ANCHOR - Invitations Model
    code = StringType(required=False, default=None)
    used = BooleanType(required=False, default=False)
    expires = IntType(required=False, default=None)
    used_by = StringType(required=False, default=None)
    unlimited = BooleanType(required=False, default=False)
    duration = IntType(required=False, default=None)
    specific_libraries = SpecificLibrariesType(required=False, default=[])
    plex_allow_sync = BooleanType(required=False, default=False)
    sessions = IntType(required=False, default=None)
    live_tv = BooleanType(required=False, default=True)
    used_at = DateTimeType(required=False, default=None, convert_tz=True)
    created = DateTimeType(required=False, default=datetime.utcnow(), convert_tz=True)
    hide_user = BooleanType(required=False, default=True)
    allow_download = BooleanType(required=False, default=True)


    # ANCHOR - Validate Code
    def validate_code(self, _, value: str):
        # If the code is None ignore further validation
        if value is None:
            return

        # Check that the code only contains letters and numbers
        if not isinstance(value, str) or not value.isalnum():
            raise ValidationError("Invalid code")

        # Check that the code has not been used
        if Invitations.get_or_none(Invitations.code == self.code) is not None:
            raise ValidationError("Code already exists")


    # ANCHOR - Validate expires
    def validate_expires(self, _, value: datetime):
        # Check that the expires is in the future, ignore milliseconds
        if value and (datetime.utcnow() + timedelta(minutes=int(str(value)))) < datetime.utcnow():
            raise ValidationError("Expires must be in the future")

    # ANCHOR - Validate duration
    def validate_duration(self, _, value: datetime):
        # Check that the duration is in the future, ignore milliseconds
        if value and (datetime.utcnow() + timedelta(minutes=int(str(value)))) < datetime.utcnow():
            raise ValidationError("Duration must be in the future")

    # ANCHOR - Validate specific_libraries
    def validate_specific_libraries(self, _, value):
        # Check that the value is a list
        if not isinstance(value, list):
            raise ValidationError("Invalid libraries")

        # Check that the libraries are valid
        for library_id in value:

            # Check that the library is a string
            if not isinstance(library_id, str):
                raise ValidationError("Invalid library id")

            # Check that the library exists in the database
            if not Libraries.get_or_none(Libraries.id == library_id):
                raise ValidationError(f"Invalid library {library_id}")


    # ANCHOR - Create Invitation in the Database
    def create_invitation(self) -> Invitations:
        # Create the invitation
        invitation = self.to_native()

        # Infinite function that will create a new code until it is unique in the database, only run 10 times
        def create_code():
            for _ in range(10):
                code = token_hex(3).upper()
                if not Invitations.get_or_none(Invitations.code == code):
                    return code
            raise ValidationError("Unable to generate a unique code")

        # If code is None, generate a new code
        if not invitation["code"] or not str(invitation["code"]).isalnum():
            invitation["code"] = create_code()

        # Upper case the code
        invitation["code"] = str(invitation["code"]).upper()

        # If specific_libraries is empty, set it to all libraries
        if len(invitation["specific_libraries"]) == 0:
            invitation["specific_libraries"] = [library.id for library in Libraries.select()]

        # If specific_libraries is a list, convert it to a string of comma separated values
        if isinstance(invitation["specific_libraries"], list):
            invitation["specific_libraries"] = ",".join(invitation["specific_libraries"])

        # If expires is a string or int, convert it to a utc datetime plus the total minutes
        if invitation["expires"] and isinstance(invitation["expires"], (str, int)):
            invitation["expires"] = datetime.utcnow() + timedelta(minutes=int(str(invitation["expires"])))

        # If duration is a string or int, convert it to a utc datetime plus the total minutes
        if invitation["duration"] and isinstance(invitation["duration"], (str, int)):
            invitation["duration"] = datetime.utcnow() + timedelta(minutes=int(str(invitation["duration"])))

        invitation["created"] = datetime.utcnow()

        # Create the invitation in the database
        invite: Invitations = Invitations.create(**invitation)

        # Convert specific_libraries back to a list
        invite.specific_libraries = invite.specific_libraries.split(",")

        # Set the attributes of the invite to model
        for key, value in model_to_dict(invite).items():
            setattr(self, key, value)

        return loads(dumps(model_to_dict(invite), indent=4, sort_keys=True, default=str))
