from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from models.admins import AdminsGetModel, AdminsPostModel, Admins
from helpers import (
    create_admin_user,
    convert_to_form,
    get_admins,
    get_admin_by_id,
    delete_admin_user,
    update_admin_user,
)

api = Namespace("Accounts", description="Accounts related operations", path="/accounts")

api.add_model("AdminsGetModel", AdminsGetModel)
api.add_model("AdminsPostModel", AdminsPostModel)


@api.route("")
@api.route("/")
@api.doc(security=["jsonWebToken", "cookieAuth"])
class AccountsListAPI(Resource):
    """API resource for all accounts
    :functions: get, post
    """

    method_decorators = [jwt_required(), convert_to_form()]

    @api.marshal_list_with(AdminsGetModel)
    @api.doc(description="Get all accounts")
    @api.response(200, "Successfully retrieved all accounts")
    @api.response(500, "Internal server error")
    def get(self) -> tuple[list[Admins], int]:
        """Get all accounts
        returns: tuple[list[Admins], int]
        """
        
        return get_admins(), 200

    @api.expect(AdminsPostModel)
    @api.marshal_with(AdminsGetModel)
    @api.doc(description="Create a new account")
    @api.response(200, "Successfully created a new account")
    @api.response(400, "Invalid account")
    @api.response(409, "Account already exists")
    @api.response(500, "Internal server error")
    def post(self) -> tuple[Admins, int]:
        """Create a new account
        returns: tuple[Admins, int]
        """
        
        response = create_admin_user(**request.form)
        return response, 200


@api.route("/<int:admin_id>")
@api.doc(security=["jsonWebToken", "cookieAuth"])
class AccountsAPI(Resource):
    """API resource for a single account
    :functions: get, put, delete
    """
    method_decorators = [jwt_required(), convert_to_form()]

    @api.marshal_with(AdminsGetModel)
    @api.doc(description="Get an account")
    @api.response(200, "Successfully retrieved an account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def get(self, admin_id: str) -> tuple[Admins, int]:
        """Get an account
        returns: tuple[Admins, int]
        """
        
        return get_admin_by_id(admin_id), 200

    @api.expect(AdminsPostModel)
    @api.marshal_with(AdminsGetModel)
    @api.doc(description="Update an account")
    @api.response(200, "Successfully updated an account")
    @api.response(400, "Invalid account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def put(self, admin_id: int) -> tuple[Admins, int]:
        """Update an account
        :param admin_id: The id of the account to update
        :type admin_id: int

        returns: tuple[Admins, int]
        """
        
        response = update_admin_user(admin_id, **request.form)
        return response, 200

    @api.doc(description="Delete an account")
    @api.response(200, "Successfully deleted an account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def delete(self, admin_id: str) -> tuple[dict[str, str], int]:
        """Delete an account
        :param admin_id: The id of the account to delete
        :type admin_id: str
        
        returns: tuple[Admins, int]
        """
        
        delete_admin_user(admin_id)
        return {"message": "Account deleted"}, 200
