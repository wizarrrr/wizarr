from app.blueprints.media_common.routes import create_media_blueprint

# Create the komga blueprint using the common factory
komga_bp = create_media_blueprint("komga", "/komga")
