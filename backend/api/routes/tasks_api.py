from flask import Response, make_response
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

api = Namespace("Tasks", description="Tasks related operations", path="/tasks")

@api.route('')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class TasksListAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self) -> Response:
        # Import required modules here to avoid circular imports
        from app.scheduler import get_schedule

        return make_response(get_schedule(), 200)


@api.route('/<string:task_id>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class TasksAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self, task_id: str) -> Response:
        # Import required modules here to avoid circular imports
        from app.scheduler import get_task

        return make_response(get_task(task_id), 200)

@api.route('/<string:task_id>/run')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class TasksRunAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self, task_id: str) -> Response:
        # Import required modules here to avoid circular imports
        from app.scheduler import run_task

        # Run the task
        run_task(task_id)

        return make_response({ "msg": f"Task {task_id} has been run" }, 200)
