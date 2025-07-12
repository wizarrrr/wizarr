from app.blueprints.media_common.routes import create_media_blueprint

# Create the emby blueprint using the common factory
emby_bp = create_media_blueprint("emby", "/emby")
