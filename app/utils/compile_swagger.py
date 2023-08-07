from flask_restx import Api
from json import dumps
from os import path

def compile_swagger(api: Api):
    """Compile the Swagger JSON file"""
    base_dir = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))

    # Compile Swagger JSON file
    swagger_data = api.__schema__
    with open(path.join(base_dir, "../", "swagger.json"), "w", encoding="utf-8") as f:
        f.write(dumps(swagger_data))

    # Clear log file contents on startup
    if path.exists(path.join(base_dir, "../", "database", "logs.log")):
        with open(path.join(base_dir, "../", "database", "logs.log"), "w", encoding="utf-8") as f:
            f.write("")
