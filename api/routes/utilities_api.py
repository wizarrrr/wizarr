from flask import redirect, request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Model, Namespace, Resource, fields

api = Namespace('Utilities', description='Utility functions', path="/utilities")

@api.route('/detect-server')
class DetectServerAPI(Resource):
    """Detect server type"""

    def get(self):
        """Detect server type"""
        from app.utils.media_server import detect_server
        return detect_server(request.args.get('server_url'))

@api.route('/verify-server')
class VerifyServerAPI(Resource):
    """Verify server connection credentials"""

    def get(self):
        """Verify server connection credentials"""
        from app.utils.media_server import verify_server
        return verify_server(request.args.get('server_url'), request.args.get('api_key'))
