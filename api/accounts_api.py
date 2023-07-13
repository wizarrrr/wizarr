
from unittest import TestCase, mock

from flask import jsonify
from flask_restx import Namespace, Resource
from peewee import IntegrityError, SqliteDatabase
from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel, Field

from api.helpers import try_catch
from models import Admins, AdminsModel

api = Namespace("Accounts", description="Accounts related operations", path="/accounts")

@api.route('/')
class AccountsListAPI(Resource):

    @try_catch
    def get(self) -> dict:
        admins = Admins.select()
        response: dict[str, dict] = {admin.username: self._remove_password(admin) for admin in admins}
        return jsonify(response)

    def _remove_password(self, admin: Admins) -> dict:
        admin_dict: dict[str, str] = model_to_dict(admin)
        admin_dict.pop('password', None)
        return admin_dict

    @try_catch
    def post(self) -> dict:
        accounts: dict[str, str] = { key: value for key, value in self.request.form.items() }


        for username, password in accounts.items():
            Admins.create(username=username, password=password)

        return self.get()
    
    
@api.route('/<string:username>')
class AccountsAPI(Resource):
    
    @try_catch
    def get(self, username: str) -> dict:
        admin = Admins.get(Admins.username == username)
        return jsonify(self._remove_password(admin))

    def _remove_password(self, admin: Admins) -> dict:
        admin_dict: dict[str, str] = model_to_dict(admin)
        admin_dict.pop('password', None)
        return admin_dict
    
    @try_catch
    def put(self, username: str) -> dict:
        class Put(BaseModel):
            data: dict[str, str] = Field(description="The account to update")

        account: dict[str, str] = { key: value for key, value in self.request.form.items() }

        Put(data=account)

        admin = Admins.get(Admins.username == username)
        admin.username = account['username']
        admin.password = account['password']
        admin.save()

        return self.get(admin.username)

