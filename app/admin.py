from typing import Set
from flask import request, redirect,render_template, abort, jsonify
from app import app, auth, Settings, VERSION
from werkzeug.security import generate_password_hash
from plexapi.server import PlexServer
import logging
import requests


@app.route('/settings', methods=["GET", "POST"])
def preferences():
  if not Settings.select().where(Settings.key == 'admin_username').exists():
    
    if request.method == 'GET':
      return render_template("register_admin.html")
    
    elif request.method == 'POST':
      username = request.form.get("username")
      password = request.form.get("password")
      
      if password != request.form.get("confirm-password"):
        return render_template("register_admin.html", error="Passwords do not match.")
      
      if len(username) <3 or len(username) > 15:
        return render_template("register_admin.html", error="Username must be between 3 and 15 characters.")
      
      if len(password) <3 or len(password) > 20:
        return render_template("register_admin.html", error="Password must be between 3 and 20 characters.")
      hash = generate_password_hash(password, "sha256")
      Settings.create(key="admin_username", value=username)
      Settings.create(key="admin_password", value=hash)
      return redirect("/settings")
  
  elif Settings.select().where(Settings.key == 'admin_username').exists() and not Settings.select().where(Settings.key == "plex_verified", Settings.value == "True").exists():
    
    if request.method == 'GET':
      return render_template("verify_plex.html")
    
    elif request.method == 'POST':
      name = request.form.get("name")
      plex_url = request.form.get("plex_url")
      plex_token = request.form.get("plex_token")

      #Getting Libraries Properly
      libraries = []
      library_count = int(request.form.get("library_count"))
      for library in range(library_count+1):

        if request.form.get("plex_library_" + str(library)):
          libraries.append(request.form.get("plex_library_" + str(library)))
      libraries = ', '.join(libraries)
      if not libraries:
        return render_template("settings.html", error="You must select at least one library.")
      overseerr_url = request.form.get("overseerr_url")
      Settings.create(key="plex_name", value=name)
      Settings.create(key="plex_url", value=plex_url)
      Settings.create(key="plex_token", value=plex_token)
      Settings.create(key="plex_libraries", value=libraries)
      Settings.create(key="overseerr_url", value=overseerr_url)
      Settings.create(key="plex_verified", value="True")
      return redirect("/")
  elif Settings.select().where(Settings.key == 'admin_username').exists() and Settings.select().where(Settings.key == "plex_verified", Settings.value == "True").exists():
      return redirect('/settings/')


@app.route('/settings/', methods=["GET", "POST"])
@auth.login_required
def secure_settings():
    if request.method == 'GET':
      plex_name = Settings.get(Settings.key == "plex_name").value
      plex_url = Settings.get(Settings.key == "plex_url").value
      plex_libraries = Settings.get(Settings.key == "plex_libraries").value
      overseerr_url = Settings.get(Settings.key == "overseerr_url").value
      return render_template("settings.html", plex_name=plex_name, plex_url=plex_url, plex_libraries=plex_libraries, overseerr_url=overseerr_url)
    
    elif request.method == 'POST':
      name = request.form.get("name")
      plex_url = request.form.get("plex_url")
      plex_token = request.form.get("plex_token")
      
      #Getting Libraries Properly
      libraries = []
      library_count = int(request.form.get("library_count"))
      for library in range(library_count+1):

        if request.form.get("plex_library_" + str(library)):
          libraries.append(request.form.get("plex_library_" + str(library)))
      libraries = ', '.join(libraries)

      if not libraries:
        return render_template("settings.html", error="You must select at least one library.")
      overseerr_url = request.form.get("overseerr_url")
      try:
        plex = PlexServer(plex_url, token=plex_token)
      except Exception as e:
          logging.error(str(e))
          if "unauthorized" in str(e):
            error = "It is likely that your token does not work."
          else:
            error = "Unable to connect to your Plex server. See Logs for more information."
          return render_template("verify_plex.html", error=error)
      Settings.update(value=name).where(Settings.key == "plex_name").execute()
      Settings.update(value=plex_url).where(Settings.key == "plex_url").execute()
      Settings.update(value=plex_token).where(Settings.key == "plex_token").execute()
      Settings.update(value=libraries).where(Settings.key == "plex_libraries").execute()
      Settings.update(value=overseerr_url).where(Settings.key == "overseerr_url").execute()
      return redirect("/")

@app.route('/scan', methods=["POST"])
def scan():
  plex_url = request.args.get('plex_url')
  plex_token = request.args.get('plex_token')
  if not plex_url or not plex_token:
    abort(400)
  try:
    plex = PlexServer(plex_url, token=plex_token)
    libraries_raw = plex.library.sections()
  except:
    abort(400)
  libraries = []
  for library in libraries_raw:
    libraries.append(library.title)
  return jsonify(libraries)

def needUpdate():
  try:
    r = requests.get(url = "https://wizarr.jaseroque.com/check")
    data = r.content
    if VERSION != data:
      return True
    else:
      return False
  except:
    #Nevermind
    return False
