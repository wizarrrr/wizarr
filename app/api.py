from flask import request

from app import app, partials
from api.settings_api import SettingsController


# All SETTINGS API routes


# All NOTIFICATIONS API routes
# Get all notifications
@app.get('/api/notifications')
def api_notifications_get():
    return controllers.get_notifications(request)

# Post a new notification
@app.post('/api/notifications')
def api_notifications_post():
    return controllers.post_notifications(request)

# @get.route('/api/notifications/<path:id>')
# def api_notifications_id_get(path_id):
#     return controllers.get_notification(path_id)
#     hx_template = request.headers.get("Hx-Template")

#     return (partials.notifications_partials(hx_template) if hx_template else result)

# @put.route('/api/notifications/<path:id>')
# def api_notifications_id_put(path_id):
#     return controllers.put_notification(id, request.form)
#     hx_template = request.headers.get("Hx-Template")

#     return (partials.notifications_partials(hx_template) if hx_template else result)

@app.delete('/api/notifications/<path:path_id>')
def api_notifications_id_delete(path_id):
    return controllers.delete_notification(path_id)



# All ACCOUNTS API routes
# Get all accounts
@app.get('/api/accounts')
def api_accounts_get():
    return controllers.get_accounts(request)

# Post a new account
@app.post('/api/accounts')
def api_accounts_post():
    return controllers.post_accounts(request)

# Get the account with the specified ID
@app.get('/api/accounts/<int:admin_id>')
def api_accounts_id_get(admin_id):
    return controllers.get_accounts_id(admin_id)

# Put the account with the specified ID
@app.put('/api/accounts/<int:admin_id>')
def api_accounts_id_put(admin_id):
    return controllers.put_accounts_id(admin_id, request.form)

# Delete the account with the specified ID
@app.delete('/api/accounts/<int:admin_id>')
def api_accounts_id_delete(admin_id):
    return controllers.delete_accounts_id(admin_id)

# All ACCOUNTS SESSIONS API routes
# Get all sessions for the account with the specified ID
@app.get('/api/accounts/<int:admin_id>/sessions')
def api_accounts_sessions_get(admin_id):
    return controllers.get_accounts_sessions(admin_id)

# Delete all sessions for the account with the specified ID
@app.delete('/api/accounts/<int:admin_id>/sessions')
def api_accounts_sessions_delete(admin_id):
    return controllers.delete_accounts_sessions(admin_id)

# Delete a session for the account with the specified ID
@app.delete('/api/accounts/<int:admin_id>/sessions/<int:session_id>')
def api_accounts_session_id_delete(admin_id, session_id):
    return controllers.delete_accounts_session(admin_id, session_id)

# All ACCOUNTS API API routes
# Get all API keys for the account with the specified ID
@app.get('/api/accounts/<int:admin_id>/api')
def api_accounts_api_get(admin_id):
    return controllers.get_accounts_api(admin_id)

# Post a new API key for the account with the specified ID
@app.post('/api/accounts/<int:admin_id>/api')
def api_accounts_api_post(admin_id):
    return controllers.post_accounts_api(admin_id, request.form)

# Delete all API keys for the account with the specified ID
@app.delete('/api/accounts/<int:admin_id>/api')
def api_accounts_api_delete(admin_id):
    return controllers.delete_accounts_api(admin_id)

# Delete an API key for the account with the specified ID
@app.delete('/api/accounts/<int:admin_id>/api/<int:api_id>')
def api_accounts_api_id_delete(admin_id, api_id):
    return controllers.delete_accounts_api_id(admin_id, api_id)



# @get.route('/api/libraries')
# def api_libraries_get():
#     return controllers.get_libraries(request)

@app.post('/api/libraries')
def api_libraries_post():
    return controllers.post_libraries(request)



@app.get('/api/admin/users')
def api_admin_users_get():
    return controllers.get_admin_users(request)

@app.post('/api/admin/users')
def api_admin_users_post():
    return controllers.post_admin_users(request)


@app.post('/api/scan-libraries')
def api_scan_libraries_post():
    return controllers.post_scan_libraries(request)

# Login and logout routes
@app.post('/login')
def login_post():
    return controllers.login(request.form.get("username"), request.form.get("password"), request.form.get("remember") == "on")

@app.get('/logout')
def logout_get():
    return controllers.logout()
