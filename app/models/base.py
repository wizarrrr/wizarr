from peewee import Model, SqliteDatabase

db = SqliteDatabase("./database/database.db")

class BaseModel(Model):
    class Meta:
        database = db
        