from peewee import Model, SqliteDatabase
from os import path

# Get the path of current file
current_dir = path.dirname(path.realpath(__file__))

# Get the base directory from the current directory
base_dir = path.abspath(path.join(current_dir, "../.."))

db = SqliteDatabase(path.join(base_dir, "database", "database.db"))

class BaseModel(Model):
    class Meta:
        database = db

