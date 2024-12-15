from json import dumps, loads
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict
from peewee import fn
from app.models.database import db

from app.models.database.onboarding import Onboarding as OnboardingDB

api = Namespace("Onboarding", description="Onboarding related operations", path="/onboarding")

@api.route("")
class OnboardingListApi(Resource):
    """API resource for all onboarding pages"""

    @api.doc(security="jwt")
    def get(self):
        """Get onboarding pages"""
        response = list(OnboardingDB.select().order_by(OnboardingDB.order).dicts())
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200

    @api.doc(security="jwt")
    @jwt_required()
    def post(self):
        """Create onboarding page"""
        value = request.form.get("value")
        enabled = request.form.get("enabled") in ["true", "True", "1"]
        max_order = OnboardingDB.select(fn.MAX(OnboardingDB.order)).scalar() or 0
        new_order = max_order + 1
        onboarding_page = OnboardingDB.create(order=new_order, value=value, enabled=enabled)
        onboarding_page.save()
        return { "message": "Onboarding page created", "page": model_to_dict(onboarding_page) }, 200


@api.route("/<int:onboarding_id>")
class OnboardingAPI(Resource):
    """API resource for a single onboarding page"""

    method_decorators = [jwt_required()]

    @api.doc(description="Updates a single onboarding page")
    @api.response(404, "Onboarding page not found")
    @api.response(500, "Internal server error")
    def put(self, onboarding_id: int):
        value = request.form.get("value")
        enabled = request.form.get("enabled")
        order = request.form.get("order", type=int)

        with db.atomic() as transaction:
            page = OnboardingDB.get_or_none(OnboardingDB.id == onboarding_id)
            if not page:
                return {"error": "Onboarding page not found"}, 404

            if value is not None:
                page.value = value
            if enabled is not None:
                page.enabled = enabled in ["true", "True", "1"]

            if order is not None and page.order != order:
                step = 1 if page.order > order else -1
                start, end = sorted([page.order, order])

                # Temporarily set the order of the target page to a value that won't conflict
                max_order = OnboardingDB.select(fn.MAX(OnboardingDB.order)).scalar() or 0
                page.order = max_order + 1
                page.save()

                # Shift orders of affected pages
                affected_pages = OnboardingDB.select().where(
                    OnboardingDB.id != onboarding_id,
                    OnboardingDB.order >= start,
                    OnboardingDB.order <= end,
                ).order_by(OnboardingDB.order.asc() if step > 0 else OnboardingDB.order.desc())

                for p in affected_pages:
                    p.order += step
                    p.save()

                # Finally, set the target page to its new order
                page.order = order
            page.save()  # Save the target page
        return loads(dumps(model_to_dict(page), indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Delete a single onboarding page")
    @api.response(404, "Invite not found")
    @api.response(500, "Internal server error")
    def delete(self, onboarding_id):
        """Delete onboarding page"""
        # Select the invite from the database
        onboarding_page = OnboardingDB.get_or_none(OnboardingDB.id == onboarding_id)

        # Check if the invite exists
        if not onboarding_page:
            return {"message": "Onboarding page not found"}, 404

        onboarding_page.delete_instance()

        # Update order of subsequent pages
        subsequent_pages = OnboardingDB.select().where(OnboardingDB.order > onboarding_page.order)
        for page in subsequent_pages:
            page.order -= 1
            page.save()

        return { "message": "Onboarding page deleted successfully" }, 200
