import os
import time
from flask import Response, request, send_file
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from io import BytesIO
from queue import Queue
from threading import Event, local
from concurrent.futures import ThreadPoolExecutor
import atexit

api = Namespace("Logging", description="Logging related operations", path="/logging")
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../", "database", "logs.log"))

executor = ThreadPoolExecutor(max_workers=1)
local_data = local()  # Create thread-local storage for each request

@api.route("/stream")
@api.route("/stream/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class LogStreamAPI(Resource):
    """API resource for streaming logging"""

    method_decorators = [jwt_required()]

    @staticmethod
    def read_file(filename, queue, stop_event):
        with open(filename, 'r', encoding="utf-8") as file:
            while not stop_event.is_set():
                line = file.readline()
                if not line:
                    time.sleep(0.1)  # Adjust sleep time based on your requirements
                else:
                    queue.put(line)

    @classmethod
    def start_log_reader(cls):
        if not hasattr(local_data, 'log_queue') or local_data.log_queue is None:
            local_data.log_queue = Queue()
            cls.stop_event = Event()
            executor.submit(cls.read_file, log_file, local_data.log_queue, cls.stop_event)

    @staticmethod
    def get():
        def generate():
            queue = local_data.log_queue

            try:
                while True:
                    line = queue.get()  # Get the new line from the queue
                    yield f"data: {line}\n\n"  # Send the line to the client as an Event Stream message
            except GeneratorExit:  # Client closed the connection
                if hasattr(local_data, 'log_queue') and local_data.log_queue is not None:
                    local_data.log_queue = None
                LogStreamAPI.stop_event.set()  # Signal the background thread to stop

        # Ensure that the client supports Event Streams
        if request.headers.get('accept') == 'text/event-stream':
            LogStreamAPI.start_log_reader()

            return Response(generate(), content_type='text/event-stream')
        else:
            return {"message": "Invalid request. This endpoint requires Event Stream support."}, 400


@api.route("/text")
@api.route("/text/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class LogAPI(Resource):
    """API resource for downloading logs"""

    method_decorators = [jwt_required()]

    @staticmethod
    def get():
        with open(log_file, "rb") as f:
            log_data = f.read()

        log_data_io = BytesIO(log_data)

        return send_file(log_data_io, mimetype="text/plain")


def cleanup_before_exit():
    """Function to be called when the server is terminated"""
    if hasattr(local_data, 'log_queue') and local_data.log_queue is not None:
        local_data.log_queue = None

# Register the cleanup function for server termination
atexit.register(cleanup_before_exit)
