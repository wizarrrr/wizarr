from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp


class JoinForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired()],
    )
    email = StringField(
        "Email",
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
        validators=[DataRequired(), Length(min=6, max=10)],
        render_kw={"minlength": 6, "maxlength": 10},
    )
