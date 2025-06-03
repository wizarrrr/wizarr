from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp


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
            Length(min=8, max=20),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$',
                message="Password must contain at least one uppercase letter, one lowercase letter, and one number.",
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    code = StringField(
        "Invite Code",
        validators=[DataRequired()],
    )
