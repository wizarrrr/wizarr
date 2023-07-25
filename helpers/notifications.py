from models.database.notifications import Notifications


def get_notifications():
    # Get all notification agents from the database
    notifications = Notifications.select()

    # Return all notification agents
    return notifications