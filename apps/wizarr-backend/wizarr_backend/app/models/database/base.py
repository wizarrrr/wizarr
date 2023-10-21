from peewee import Model, SqliteDatabase
from os import path
from definitions import DATABASE_DIR

db_file = path.join(DATABASE_DIR, "database.db")
db = SqliteDatabase(db_file)

class BaseModel(Model):
    class Meta:
        database = db
