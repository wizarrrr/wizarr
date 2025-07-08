from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, ValidationError
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, Optional


_username_validators = [
    DataRequired(),
    Length(min=3, max=15, message="Username must be 3 to 15 characters."),
]
_password_validators = [
    DataRequired(),
    Length(min=8, message="Password must be at least 8 characters."),
    Regexp(
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$',
        message="Password must contain at least one uppercase letter, one lowercase letter, and one number.",
    ),
]


class AdminCreateForm(FlaskForm):
    username = StringField("Username", validators=_username_validators)
    password = PasswordField("Password", validators=_password_validators)
    confirm  = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])


class AdminUpdateForm(FlaskForm):
    username = StringField("Username", validators=_username_validators)

    # New password can be left blank (unchanged)
    password = PasswordField("New Password", validators=[Optional()] + _password_validators[1:])
    confirm  = PasswordField("Confirm password", validators=[Optional(), EqualTo("password", message="Passwords must match.")])

    def validate(self, extra_validators=None):
        # Skip inherited validation if confirm required but password empty
        if not super().validate(extra_validators):
            return False
        # If one of password/confirm is filled, both must pass validators
        pw = self.password.data or ""
        if pw and not self.confirm.data:
            self.confirm.errors.append("Please confirm the new password.")
            return False
        return True 