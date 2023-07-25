from flask_restx import Model, fields


AdminsPostModel = Model('AdminsPostModel', {
    "username": fields.String(required=True, description="Username"),
    "password": fields.String(required=True, description="Password"),
    "email": fields.String(required=False, description="Email"),
})

AdminsGetModel = Model('AdminsGetModel', {
    "id": fields.Integer(required=True, description="The ID of the admin"),
    "username": fields.String(required=True, description="Username"),
    "email": fields.String(required=False, description="Email", allow_null=True),
    "last_login": fields.String(required=False, description="Last login", allow_null=True),
    "created": fields.String(required=False, description="The date the admin was created", allow_null=True),
})