from peewee import Model, SqliteDatabase
from os import path

current_dir = path.dirname(path.realpath(__file__))
base_dir = path.abspath(path.join(current_dir, "../", "../", "../"))
db_dir = path.join(base_dir, "database")
db_file = path.join(db_dir, "database.db")

db = SqliteDatabase(db_file)

class BaseModel(Model):
    class Meta:
        database = db

