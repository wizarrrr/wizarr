from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

from app.forms.validators import (
    USERNAME_ALLOWED_CHARS_MESSAGE,
    USERNAME_LENGTH_MESSAGE,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_PATTERN,
    strip_filter,
)


class JoinForm(FlaskForm):
    username = StringField(
        "Username",
        filters=[strip_filter],
        validators=[
            DataRequired(),
            Length(
                min=USERNAME_MIN_LENGTH,
                max=USERNAME_MAX_LENGTH,
                message=USERNAME_LENGTH_MESSAGE,
            ),
            Regexp(USERNAME_PATTERN, message=USERNAME_ALLOWED_CHARS_MESSAGE),
        ],
    )
    email = StringField(
        "Email",
        filters=[strip_filter],
        validators=[DataRequired(), Email()],
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
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    code = StringField(
        "Invite Code",
        filters=[strip_filter],
        validators=[DataRequired(), Length(min=6, max=10)],
        render_kw={"minlength": 6, "maxlength": 10},
    )
