import os

from app import create_app
from app.config import DevelopmentConfig, ProductionConfig

# Select config based on FLASK_ENV or default to production for safety
flask_env = os.getenv("FLASK_ENV", "production")
config = DevelopmentConfig if flask_env == "development" else ProductionConfig

app = create_app(config)

if __name__ == "__main__":
    app.run()
