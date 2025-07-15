from app.blueprints.media_common.routes import create_media_blueprint

# Create the audiobookshelf blueprint using the common factory
abs_bp = create_media_blueprint("audiobookshelf", "/abs")
