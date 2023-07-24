from datetime import datetime, timedelta
from json import JSONDecodeError, loads
from secrets import token_hex

from playhouse.shortcuts import model_to_dict
from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import (BaseType, BooleanType, DateTimeType, IntType,
                              StringType)

from models.invitations import Invitations
from models.libraries import Libraries


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

# Custom model to convert string datetime based on the value of minutes as an int
class IntStringType(IntType):
    """Int String Type"""

    def to_native(self, value, _):
        if isinstance(value, str):
            try:
                return datetime.utcnow() + timedelta(minutes=int(value))
            except ValueError:
                return 0

        if isinstance(value, int):
            return datetime.utcnow() + timedelta(minutes=value)

        return value

    def to_primitive(self, value, _):
        if isinstance(value, datetime):
            return int((value - datetime.utcnow()).total_seconds() / 60)

        return value


class InvitationsModel(Model):
    """Invitations Model"""

    # ANCHOR - Invitations Model
    code = StringType(required=False, default=None)
    used = BooleanType(required=False, default=False)
    expires = IntStringType(required=False, default=0)
    used_by = StringType(required=False, default=None)
    unlimited = BooleanType(required=False, default=False)
    duration = IntStringType(required=False, default=0)
    specific_libraries = SpecificLibrariesType(required=False, default=[])
    plex_allow_sync = BooleanType(required=False, default=False)
    plex_home = BooleanType(required=False, default=False)
    used_at = DateTimeType(required=False, default=None)
    created = DateTimeType(required=False, default=datetime.utcnow())


    # ANCHOR - Validate Code
    def validate_code(self, _, value: str):
        # If the code is None ignore further validation
        if value is None:
            return

        # Check that the code is a 6 character string of only letters and numbers
        if not isinstance(value, str) or len(value) != 6 or not value.isalnum():
            raise ValidationError("Invalid code")

        # Check that the code has not been used
        if Invitations.get_or_none(Invitations.code == self.code) is not None:
            raise ValidationError("Code already exists")


    # ANCHOR - Validate expires
    def validate_expires(self, _, value: datetime):
        # Check that the expires is in the future, ignore milliseconds
        if value.replace(microsecond=0) < datetime.utcnow().replace(microsecond=0):
            raise ValidationError("Expires must be in the future")


    # ANCHOR - Validate duration
    def validate_duration(self, _, value: datetime):
        # Check that the duration is in the future, ignore milliseconds
        if value.replace(microsecond=0) < datetime.utcnow().replace(microsecond=0):
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
        if not invitation["code"] or len(invitation["code"]) != 6 or not str(invitation["code"]).isalnum():
            invitation["code"] = create_code()

        # Upper case the code
        invitation["code"] = str(invitation["code"]).upper()

        # If specific_libraries is empty, set it to all libraries
        if len(invitation["specific_libraries"]) == 0:
            invitation["specific_libraries"] = [library.id for library in Libraries.select()]

        # If specific_libraries is a list, convert it to a string of comma separated values
        if isinstance(invitation["specific_libraries"], list):
            invitation["specific_libraries"] = ",".join(invitation["specific_libraries"])

        # Create the invitation in the database
        invite: Invitations = Invitations.create(**invitation)

        # Convert specific_libraries back to a list
        invite.specific_libraries = invite.specific_libraries.split(",")

        # Set the attributes of the invite to model
        for key, value in model_to_dict(invite).items():
            setattr(self, key, value)
