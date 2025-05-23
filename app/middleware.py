# app/middleware.py
from flask import request, redirect, url_for
from app.models import Settings

def require_onboarding():
    if request.path.startswith('/setup') or request.path.startswith('/static') or request.path.startswith('/settings'):
        return
    server_verified = (
        Settings.query
        .filter_by(key="server_verified")
        .first()
    )
    if not server_verified or server_verified.value != "true":
        return redirect(url_for('setup.onboarding'))