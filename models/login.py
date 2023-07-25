from flask_restx import Model, fields

LoginPostModel = Model("LoginPostModel", {
    "username": fields.String(required=True, description="Username"),
    "password": fields.String(required=True, description="Password"),
    "remember": fields.Boolean(required=False, description="Remember me", default=False)
})
