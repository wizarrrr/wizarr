from peewee import SQL, CharField, DateTimeField, IntegerField, ForeignKeyField
from app.models.database.base import BaseModel
from app.models.database.users import Users

class Notifications(BaseModel):
    id = IntegerField(primary_key=True)
    user_id = ForeignKeyField(Users, backref='notifications', on_delete='CASCADE')
    resource = CharField()
    data = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
