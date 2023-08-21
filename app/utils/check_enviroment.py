from os import getenv, path, access, W_OK, R_OK
from flask import request, render_template

def check_enviroment():
    base_dir = path.abspath(path.join(path.dirname(path.abspath(__file__)), "../", "../"))
    app_url = getenv("APP_URL")

    if app_url and app_url != request.host or not app_url:
        return render_template("errors/app_url.html"), 500

    database_path = path.abspath(path.join(base_dir, "database"))

    if not path.exists(database_path) or not path.isdir(database_path) or not access(database_path, W_OK) or not access(database_path, R_OK):
        return render_template("errors/custom.html", title="DATABASE", subtitle="Database folder not writable", description="It appears that Wizarr does not have permissions over the database folder, please make sure that the folder is writable by the user running Wizarr."), 500

    sessions_path = path.abspath(path.join(base_dir, "database", "sessions"))

    if not path.exists(sessions_path) or not path.isdir(sessions_path) or not access(sessions_path, W_OK) or not access(sessions_path, R_OK):
        return render_template("errors/custom.html", title="SESSIONS", subtitle="Sessions folder not writable", description="It appears that Wizarr does not have permissions over the sessions folder, please make sure that the folder is writable by the user running Wizarr."), 500
