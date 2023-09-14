from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource

from helpers.api import convert_to_form
from helpers.accounts import create_account, get_accounts, get_account_by_id, delete_account, update_account

from api.models.accounts import AccountsGET, AccountsPOST


api = Namespace("Accounts", description="Accounts related operations", path="/accounts")

api.add_model("AccountsGET", AccountsGET)
api.add_model("AccountsPOST", AccountsPOST)


@api.route("")
@api.route("/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class AccountsListAPI(Resource):
    """API resource for all accounts"""

    method_decorators = [jwt_required(), convert_to_form()]

    @api.marshal_list_with(AccountsGET)
    @api.doc(description="Get all accounts")
    @api.response(200, "Successfully retrieved all accounts")
    @api.response(500, "Internal server error")
    def get(self):
        """Get all accounts from the database"""
        return get_accounts(), 200


    @api.expect(AccountsPOST)
    @api.marshal_with(AccountsGET)
    @api.doc(description="Create a new account")
    @api.response(200, "Successfully created a new account")
    @api.response(400, "Invalid account")
    @api.response(409, "Account already exists")
    @api.response(500, "Internal server error")
    def post(self):
        """Create a new account"""
        return create_account(**request.form), 200


    @api.doc(description="Update account")
    @api.response(200, "Successfully updated account")
    @api.response(500, "Internal server error")
    def put(self):
        """Update account"""
        return update_account(current_user['id'], **request.form), 200


@api.route("/<int:account_id>")
@api.route("/<int:account_id>/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class AccountsAPI(Resource):
    """API resource for a single account"""

    method_decorators = [jwt_required(), convert_to_form()]

    @api.marshal_with(AccountsGET)
    @api.doc(description="Get an account")
    @api.response(200, "Successfully retrieved an account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def get(self, account_id: str):
        """Get an account"""
        return get_account_by_id(account_id), 200


    @api.expect(AccountsPOST)
    @api.marshal_with(AccountsGET)
    @api.doc(description="Update an account")
    @api.response(200, "Successfully updated an account")
    @api.response(400, "Invalid account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def put(self, account_id: int):
        """Update an account"""
        response = update_account(account_id, **request.form)
        return response, 200


    @api.doc(description="Delete an account")
    @api.response(200, "Successfully deleted an account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def delete(self, account_id: str) -> tuple[dict[str, str], int]:
        """Delete an account"""
        delete_account(account_id)
        return {"message": "Account deleted"}, 200
