from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class ApiKeyCreateForm(FlaskForm):
    """Form for creating a new API key."""

    name = StringField(
        "Key Name",
        validators=[
            DataRequired(),
            Length(min=1, max=100, message="Name must be between 1 and 100 characters"),
        ],
        render_kw={"placeholder": "Enter a descriptive name for this API key"},
    )
    submit = SubmitField("Create API Key")
