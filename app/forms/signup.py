from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class SignupForm(FlaskForm):
    name = StringField(_l("Your name"), validators=[DataRequired(), Length(max=100)])
    email = StringField(
        _l("Email address"), validators=[DataRequired(), Email(), Length(max=254)]
    )
    message = TextAreaField(
        _l("How do you know the server owner?"),
        validators=[Optional(), Length(max=1000)],
    )
    website = StringField(validators=[Optional(), Length(max=200)])


class SignupSettingsForm(FlaskForm):
    enabled = BooleanField(_l("Allow public access requests"))


class ReviewSignupForm(FlaskForm):
    server_id = SelectField(_l("Media server"), coerce=int, validators=[DataRequired()])


class SignupActionForm(FlaskForm):
    """CSRF protection for decisions and email retries."""
