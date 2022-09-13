import logging
import secrets
import string
import os
import datetime
from flask import request, redirect,render_template, abort, make_response
from app import app, Invitations, auth
from plexapi.server import PlexServer

plex = PlexServer(os.getenv("PLEX_URL"), os.getenv("PLEX_TOKEN"))

def check_plex_credentials():
  logging.info("Checking Plex Credentials from Env variables.")
  try:
    plex.myPlexAccount()
  except (IOError,NameError) as e: 
    logging.error('Could not start Wizarr, check ENV variables. ', str(e))
    exit()

@app.route('/')
def redirect_to_invite():
  return redirect('/invite')


@app.route("/j/<code>", methods=["GET"])
def welcome(code):
  if not Invitations.select().where(Invitations.code == code).exists():
    return abort(401)
  resp = make_response(render_template('welcome.html', name=os.getenv("PLEX_NAME"), code=code))
  resp.set_cookie('code', code)
  return resp
  

@app.route("/join", methods=["GET", "POST"])
def join():
  if request.method == "POST":
    error = None
    code = request.form.get('code')
    email = request.form.get("email")
    if not Invitations.select().where(Invitations.code == code).exists():
      return render_template("join.html", name = os.getenv("PLEX_NAME"), code = code, code_error="That invite code does not exist.", email=email)
    if Invitations.select().where(Invitations.code == code, Invitations.used == True).exists():
          return render_template("join.html", name = os.getenv("PLEX_NAME"), code = code, code_error="That invite code has already been used.", email=email)
    try:
      sections = (os.environ.get("PLEX_SECTIONS").split(","))
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
      else:
        logging.error(str(e))
        error = "Something went wrong. Please try again or contact an administrator."
      return render_template("join.html", name = os.getenv("PLEX_NAME"), code = code, email_error=error, email=email)
  else:
    code = request.cookies.get('code')
    if code:
      return render_template("join.html", name = os.getenv("PLEX_NAME"), code = code)
    else:
      return  render_template("Join.html", name = os.getenv("PLEX_NAME"))
    
  
@app.route('/setup', methods=["GET"])
def setup():
  return render_template("setup.html")

@app.route('/invite', methods=["GET", "POST"])
@auth.login_required
def invite():
  if request.method == "POST":
    try:
      code = request.form.get("code").upper()
      if not len(code) == 6:
        return abort(401)
      print("doing fine")
    except:
      code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    if Invitations.get_or_none(code=code):
      return abort(401) #Already Exists
    Invitations.create(code=code, used=False, created=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    link = os.getenv("APP_URL") + "/j/" + code
    invitations = Invitations.select().order_by(Invitations.created.desc())
    return render_template("invite.html", link = link, invitations=invitations)
  else:
    invitations = Invitations.select().order_by(Invitations.created.desc())
    return render_template("invite.html", invitations=invitations)
  
@app.route('/invite/delete=<code>', methods=["GET"])
@auth.login_required
def delete(code):
  Invitations.delete().where(Invitations.code == code).execute()
  return redirect('/invite')

@app.route('/setup/requests', methods=["GET"])
def requests():
  return render_template("requests.html", overseerr_url=os.getenv("OVERSEERR_URL"))

