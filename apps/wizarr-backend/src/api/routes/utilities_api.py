from flask import redirect, request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Model, Namespace, Resource, fields
from app.security import is_setup_required

api = Namespace('Utilities', description='Utility functions', path="/utilities")

@api.route('/detect-server')
class DetectServerAPI(Resource):
    """Detect server type"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    def get(self):
        """Detect server type"""
        from app.utils.media_server import detect_server
        return detect_server(request.args.get('server_url'))

@api.route('/verify-server')
class VerifyServerAPI(Resource):
    """Verify server connection credentials"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    def get(self):
        """Verify server connection credentials"""
        from app.utils.media_server import verify_server
        return verify_server(request.args.get('server_url'), request.args.get('api_key'))

@api.route('/scan-servers')
class ScanServersAPI(Resource):
    """Scan for Media Servers on the network"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    def get(self):
        """Scan for Media Servers on the network"""
        from app.utils.media_server import scan_network, get_subnet_from_ip

        subnet = request.args.get('subnet', None)
        ip = request.args.get('ip', None)

        target = str(subnet) if subnet else str(get_subnet_from_ip(str(ip))) if ip else None

        return scan_network(target=target)
