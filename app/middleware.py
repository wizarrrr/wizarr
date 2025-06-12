# app/middleware.py
from flask import request, redirect, url_for
from app.models import Settings, MediaServer

def require_onboarding():
    if request.path.startswith('/setup') or request.path.startswith('/static') or request.path.startswith('/settings'):
        return
    # Check if an admin user exists
    admin_setting = Settings.query.filter_by(key="admin_username").first()
    if not admin_setting or not admin_setting.value:
        return redirect(url_for('setup.onboarding'))
    # Require at least one MediaServer to exist
    if not MediaServer.query.first():
        return redirect(url_for('setup.onboarding'))