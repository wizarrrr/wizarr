from peewee import SQL, CharField, DateTimeField, IntegerField, BooleanField
from app.models.database.base import BaseModel

class Accounts(BaseModel):
    id = IntegerField(primary_key=True)
    avatar = CharField(null=True, default=None)
    display_name = CharField(null=True, default=None)
    username = CharField(unique=True)
    password = CharField()
    email = CharField(null=True, unique=True, default=None)
    role = CharField(default="user")
    tutorial = BooleanField(default=False)
    last_login = DateTimeField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])

    def save(self, *args, **kwargs):
        if self.role not in ["admin", "moderator", "user"]:
            raise ValueError("Invalid role value")
        super().save(*args, **kwargs)
