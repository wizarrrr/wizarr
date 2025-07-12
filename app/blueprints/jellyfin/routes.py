from app.blueprints.media_common.routes import create_media_blueprint

# Create the jellyfin blueprint using the common factory
jellyfin_bp = create_media_blueprint("jellyfin", "/jf")
