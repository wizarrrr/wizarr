from json import dumps, loads
from typing import Optional

from schematics.models import Model as SchematicsModel

from app.models.database.notifications import Notifications


class Model(SchematicsModel):
    """Extend the Schematics Model class to add additional functionality"""

    def save(self, user_id: Optional[int | str] = None):
        # Get the user id from the current user if no user id is provided
        if user_id is None:
            from flask_jwt_extended import current_user
            user_id = current_user['id']

        # # Create a new notification in the database
        new_notification = Notifications.create(
            user_id=user_id,
            resource=self.resource,
            data=self.to_json()
        )

        # # Save the notification in the database
        new_notification.save()

    def to_json(self, role=None, app_data=None, **kwargs):
        data = super().to_primitive(role, app_data, **kwargs)
        return dumps(data)

    def from_json(self, raw_data, recursive=False, **kwargs):
        data = loads(raw_data)
        return super().import_data(data, recursive, **kwargs)


