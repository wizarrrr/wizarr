from flask import redirect, request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Model, Namespace, Resource, fields

api = Namespace('Stream', description='Create a live notification stream', path="/stream")

@api.route('')
class StreamAPI(Resource):
    
    method_decorators = [jwt_required()]
    
    def get(self):
        from app import sse
        
        code = current_user.get('username').encode("utf-8").hex()
        sse.announcer(code)
        return redirect(f"/api/stream/{code}")


@api.route('/<path:stream_id>')
class StreamGetAPI(Resource):
    
    method_decorators = [jwt_required()]
    
    def get(self, stream_id):        
        from app import sse

        user_id = bytes.fromhex(stream_id).decode("utf-8")
        
        if user_id != current_user.get('username'):
            return "Unauthorized", 401
        
        return sse.response(stream_id)
