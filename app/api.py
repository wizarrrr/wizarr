from flask import request

from app import app, controllers, partials


# All SETTINGS API routes
@app.get('/api/settings')
def api_settings_get():
    # Get all settings
    result = controllers.get_settings()

    # If the request is a hx-request, return the partial instead
    if request.headers.get("Hx-Request") == "true":
        subpath = request.headers.get("Hx-Template")
        return partials.settings_partials(subpath)

    # Otherwise, return the JSON result
    return result

@app.post('/api/settings')
def api_settings_post():
    # Post the settings
    result = controllers.post_settings(request.form)

    # If the request is a hx-request, return the partial instead
    if request.headers.get("Hx-Request") == "true":
        subpath = request.headers.get("Hx-Template")
        return partials.settings_partials(subpath)

    # Otherwise, return the JSON result
    return result

@app.get('/api/settings/<path:path_id>')
def api_settings_id_get(path_id):
    # Get the setting with the specified ID
    result = controllers.get_setting(path_id)

    # If the request is a hx-request, return the partial instead
    if request.headers.get("Hx-Request") == "true":
        return partials.settings_partials(request.headers.get("Hx-Template"))

    # Otherwise, return the JSON result
    return result

@app.put('/api/settings/<path:path_id>')
def api_settings_id_put(path_id):
    # Put the setting with the specified ID
    result = controllers.put_setting(path_id, request.form)

    # If the request is a hx-request, return the partial instead
    if request.headers.get("Hx-Request") == "true":
        return partials.settings_partials(request.headers.get("Hx-Template"))

    # Otherwise, return the JSON result
    return result

@app.delete('/api/settings/<path:path_id>')
def api_settings_id_delete(path_id):
    # Delete the setting with the specified ID
    result = controllers.delete_setting(path_id)

    # If the request is a hx-request, return the partial instead
    if request.headers.get("Hx-Request") == "true":
        return partials.settings_partials(request.headers.get("Hx-Template"))

    # Otherwise, return the JSON result
    return result



# All NOTIFICATIONS API routes
@app.get('/api/notifications')
def api_notifications_get():
    return controllers.get_notifications(request)

@app.post('/api/notifications')
def api_notifications_post():
    return controllers.post_notifications(request)

# @get.route('/api/notifications/<path:id>')
# def api_notifications_id_get(path_id):
#     result = controllers.get_notification(path_id)
#     hx_template = request.headers.get("Hx-Template")

#     return (partials.notifications_partials(hx_template) if hx_template else result)

# @put.route('/api/notifications/<path:id>')
# def api_notifications_id_put(path_id):
#     result = controllers.put_notification(id, request.form)
#     hx_template = request.headers.get("Hx-Template")

#     return (partials.notifications_partials(hx_template) if hx_template else result)

@app.delete('/api/notifications/<path:path_id>')
def api_notifications_id_delete(path_id):
    return controllers.delete_notification(request, path_id)



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



# Login and logout routes
@app.post('/login')
def login_post():
    return controllers.login(request.form.get("username"), request.form.get("password"), request.form.get("remember"))

@app.get('/logout')
def logout_get():
    return controllers.logout()
