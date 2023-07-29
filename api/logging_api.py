from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from flask_sse.file_logging import MessageAnnouncer
from helpers.api import convert_to_form
from os import path
from flask import send_file
from io import BytesIO
from queue import Queue

api = Namespace("Logging", description="Logging related operations", path="/logging")
log_file = path.abspath(path.join(path.dirname(__file__), "../", "database", "logs.log"))
logging = MessageAnnouncer(log_file)

@api.route("/stream")
@api.route("/stream/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class LogStreamAPI(Resource):
    """API resource for all logging"""

    method_decorators = [jwt_required(), convert_to_form()]

    def get(self):
        return logging.response()


@api.route("/text")
@api.route("/text/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class LogAPI(Resource):
    """API resource for all logging"""

    method_decorators = [jwt_required(), convert_to_form()]
    log_queue = Queue()

    def generate_log_stream(self):
        while True:
            data = self.log_queue.get()
            if data is None:
                break
            yield data

    def get(self):
        with open(log_file, "rb") as f:
            log_data = f.read()

        log_data_io = BytesIO(log_data)

        return send_file(log_data_io, mimetype="text/plain")
