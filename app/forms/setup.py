from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

from app.forms.validators import (
    USERNAME_ALLOWED_CHARS_MESSAGE,
    USERNAME_LENGTH_MESSAGE,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_PATTERN,
    strip_filter,
)


class AdminAccountForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(
                min=USERNAME_MIN_LENGTH,
                max=USERNAME_MAX_LENGTH,
                message=USERNAME_LENGTH_MESSAGE,
            ),
            Regexp(USERNAME_PATTERN, message=USERNAME_ALLOWED_CHARS_MESSAGE),
        ],
        filters=[strip_filter],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters."),
            Regexp(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$",
                message="Password must contain at least one uppercase letter, one lowercase letter, and one number.",
            ),
        ],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
