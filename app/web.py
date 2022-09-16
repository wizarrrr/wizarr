import logging
import secrets
import string
import os
import requests
import datetime
from flask import request, redirect,render_template, abort, make_response
from app import app, Invitations, auth, Settings, VERSION
from plexapi.server import PlexServer


def getValue(value):
  if value == "overseerr_url":
    if os.getenv("OVERSEERR_URL"):
      print("ENV VARIABLES ARE DEPRECATED, PLEASE REMOVE THEM AND VISIT THE /settings PAGE")
      return os.getenv("OVERSEERR_URL")
    elif Settings.select().where(Settings.key == "overseerr_url").exists():
      return Settings.get(Settings.key == "overseerr_url").value
  if value == "plex_name":
    if os.getenv("PLEX_NAME"):
      print("ENV VARIABLES ARE DEPRECATED, PLEASE REMOVE THEM AND VISIT THE /settings PAGE")
      return os.getenv("PLEX_NAME")
    elif Settings.select().where(Settings.key == "plex_name").exists():
      return Settings.get(Settings.key == "plex_name").value
  if value == "plex_token":
    if os.getenv("PLEX_TOKEN"):
      print("ENV VARIABLES ARE DEPRECATED, PLEASE REMOVE THEM AND VISIT THE /settings PAGE")
      return os.getenv("PLEX_TOKEN")
    elif Settings.select().where(Settings.key == "plex_token").exists():
      return Settings.get(Settings.key == "plex_token").value
  if value == "plex_libraries":
    if os.getenv("PLEX_SECTIONS"):
      print("ENV VARIABLES ARE DEPRECATED, PLEASE REMOVE THEM AND VISIT THE /settings PAGE")
      return (os.environ.get("PLEX_SECTIONS").split(","))
    elif Settings.select().where(Settings.key == "plex_libraries").exists():
      return list((Settings.get(Settings.key == "plex_libraries").value).split(", "))
  if value == "plex_url":
    if os.getenv("PLEX_URL"):
      print("ENV VARIABLES ARE DEPRECATED, PLEASE REMOVE THEM AND VISIT THE /settings PAGE")
      return os.getenv("PLEX_URL")
    elif Settings.select().where(Settings.key == "plex_url").exists():
      return Settings.get(Settings.key == "plex_url").value
  else:
    return

@app.route('/')
def redirect_to_invite():
  if not Settings.select().where(Settings.key == 'admin_username').exists():
    return redirect('/settings')
  return redirect('/invite')


@app.route("/j/<code>", methods=["GET"])
def welcome(code):
  if not Invitations.select().where(Invitations.code == code).exists():
    return abort(401)
  resp = make_response(render_template('welcome.html', name=getValue("plex_name"), code=code))
  resp.set_cookie('code', code)
  return resp
  

@app.route("/join", methods=["GET", "POST"])
def join():
  if request.method == "POST":
    error = None
    code = request.form.get('code')
    email = request.form.get("email")
    if not Invitations.select().where(Invitations.code == code).exists():
      return render_template("join.html", name = getValue("plex_name"), code = code, code_error="That invite code does not exist.", email=email)
    if Invitations.select().where(Invitations.code == code, Invitations.used == True).exists():
      return render_template("join.html", name = getValue("plex_name"), code = code, code_error="That invite code has already been used.", email=email)
    if Invitations.select().where(Invitations.code == code, Invitations.used_by == email, Invitations.expires < datetime.datetime.now()).exists():
      return render_template("join.html", name = getValue("plex_name"), code = code, code_error="That invite code has expired.", email=email)
    try:
      sections = getValue("plex_libraries")
      plex = PlexServer(getValue("plex_url"),getValue("plex_token"))
      plex.myPlexAccount().inviteFriend(user=email, server=plex, sections=sections)
      Invitations.update(used=True, used_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
      return redirect("/setup")
    except Exception as e:
      if 'Unable to find user' in str(e):
        error = "That email does not match any Plex account. Please try again."
        logging.error("Unable to find user: " + email)
      elif "You're already sharing this server" in str(e):
        error = "This user is already invited to this server."
        logging.error("User already shared: " + email)
      elif "The username or email entered appears to be invalid." in str(e):
        error = "The email entered appears to be invalid."
        logging.error("Invalid email: " + email)
      else:
        logging.error(str(e))
        error = "Something went wrong. Please try again or contact an administrator."
      return render_template("join.html", name = getValue("plex_name"), code = code, email_error=error, email=email)
  else:
    code = request.cookies.get('code')
    if code:
      return render_template("join.html", name = getValue("plex_name"), code = code)
    else:
      return  render_template("join.html", name = getValue("plex_name"))
    
  
@app.route('/setup', methods=["GET"])
def setup():
  return render_template("setup.html")

def needUpdate():
  try:
    data = str(requests.get(url = "https://wizarr.jaseroque.com/check").text)
    print(data)
    if VERSION != data:
      return True
    else:
      return False
  except:
    #Nevermind
    return False


@app.route('/invite', methods=["GET", "POST"])
@auth.login_required
def invite():
  update_msg = False
  if os.getenv("ADMIN_USERNAME"):
    update_msg = True
  if request.method == "POST":
    try:
      code = request.form.get("code").upper()
      if not len(code) == 6:
        return abort(401)
    except:
      code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    if Invitations.get_or_none(code=code):
      return abort(401) #Already Exists
    expires = None
    print(request.form.get("expires"))
    if request.form.get("expires") == "day":
      expires = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    if request.form.get("expires") == "week":
      expires = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    if request.form.get("expires") == "month":
      expires = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    Invitations.create(code=code, used=False, created=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), expires=expires)
    link = os.getenv("APP_URL") + "/j/" + code
    invitations = Invitations.select().order_by(Invitations.created.desc())
    return render_template("invite.html", link = link, invitations=invitations)
  else:
    invitations = Invitations.select().order_by(Invitations.created.desc())
    needUpdate()
    return render_template("invite.html", invitations=invitations, update_msg=update_msg, needUpdate=needUpdate())
  
@app.route('/invite/delete=<code>', methods=["GET"])
@auth.login_required
def delete(code):
  Invitations.delete().where(Invitations.code == code).execute()
  return redirect('/invite')

@app.route('/setup/requests', methods=["GET"])
def plex_requests():
  if getValue("overseerr_url"):
    return render_template("requests.html", overseerr_url=getValue("overseerr_url"))
  else:
    return redirect("/setup/tips")

@app.route('/setup/tips')
def tips():
  return render_template("tips.html")


@app.errorhandler(500)
def server_error(e):
  return render_template('500.html'), 500

@app.errorhandler(404)
def server_error(e):
  return render_template('404.html'), 404

@app.errorhandler(401)
def server_error(e):
  return render_template('401.html'), 401