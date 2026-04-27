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
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.services.password_reset import get_password_reset_policy

        self.policy = get_password_reset_policy()

    def validate_password(self, field):
        from app.services.password_reset import validate_password_against_policy

        # Use the same policy as password resets
        context = [self.username.data, self.email.data]
        errors = validate_password_against_policy(
            field.data, self.policy, context_list=context
        )
        if errors:
            raise ValueError("; ".join(errors))

    code = StringField(
        "Invite Code",
        filters=[strip_filter],
        validators=[DataRequired(), Length(min=6, max=10)],
        render_kw={"minlength": 6, "maxlength": 10},
    )
