"""
flask_httpauth
==================

This module provides Basic and Digest HTTP authentication for Flask routes.

:copyright: (C) 2014 by Miguel Grinberg.
:license:   MIT, see LICENSE for more details.
"""
import hmac
from base64 import b64decode
from functools import wraps
from hashlib import md5
from random import Random, SystemRandom
from flask import request, make_response, session, g, Response, current_app
from werkzeug.datastructures import Authorization


class HTTPAuth(object):
    def __init__(self, scheme=None, realm=None, header=None):
        self.scheme = scheme
        self.realm = realm or "Authentication Required"
        self.header = header
        self.get_password_callback = None
        self.get_user_roles_callback = None
        self.auth_error_callback = None

        def default_get_password(username):
            return None

        def default_auth_error(status):
            return "Unauthorized Access", status

        self.get_password(default_get_password)
        self.error_handler(default_auth_error)

    def is_compatible_auth(self, headers):
        if self.header is None or self.header == 'Authorization':
            try:
                scheme, _ = request.headers.get('Authorization', '').split(
                    None, 1)
            except ValueError:
                # malformed Authorization header
                return False
            return scheme == self.scheme
        else:
            return self.header in headers

    def get_password(self, f):
        self.get_password_callback = f
        return f

    def get_user_roles(self, f):
        self.get_user_roles_callback = f
        return f

    def error_handler(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            res = self.ensure_sync(f)(*args, **kwargs)
            check_status_code = not isinstance(res, (tuple, Response))
            res = make_response(res)
            if check_status_code and res.status_code == 200:
                # if user didn't set status code, use 401
                res.status_code = 401
            if 'WWW-Authenticate' not in res.headers.keys():
                res.headers['WWW-Authenticate'] = self.authenticate_header()
            return res
        self.auth_error_callback = decorated
        return decorated

    def authenticate_header(self):
        return '{0} realm="{1}"'.format(self.scheme, self.realm)

    def get_auth(self):
        auth = None
        if self.header is None or self.header == 'Authorization':
            auth = request.authorization
            if auth is None and 'Authorization' in request.headers:
                # Flask/Werkzeug do not recognize any authentication types
                # other than Basic or Digest, so here we parse the header by
                # hand
                try:
                    auth_type, token = request.headers['Authorization'].split(
                        None, 1)
                    auth = Authorization(auth_type, {'token': token})
                except (ValueError, KeyError):
                    # The Authorization header is either empty or has no token
                    pass
        elif self.header in request.headers:
            # using a custom header, so the entire value of the header is
            # assumed to be a token
            auth = Authorization(self.scheme,
                                 {'token': request.headers[self.header]})

        # if the auth type does not match, we act as if there is no auth
        # this is better than failing directly, as it allows the callback
        # to handle special cases, like supporting multiple auth types
        if auth is not None and auth.type.lower() != self.scheme.lower():
            auth = None

        return auth

    def get_auth_password(self, auth):
        password = None

        if auth and auth.username:
            password = self.ensure_sync(self.get_password_callback)(
                auth.username)

        return password

    def authorize(self, role, user, auth):
        if role is None:
            return True
        if isinstance(role, (list, tuple)):
            roles = role
        else:
            roles = [role]
        if user is True:
            user = auth
        if self.get_user_roles_callback is None:  # pragma: no cover
            raise ValueError('get_user_roles callback is not defined')
        user_roles = self.ensure_sync(self.get_user_roles_callback)(user)
        if user_roles is None:
            user_roles = {}
        elif not isinstance(user_roles, (list, tuple)):
            user_roles = {user_roles}
        else:
            user_roles = set(user_roles)
        for role in roles:
            if isinstance(role, (list, tuple)):
                role = set(role)
                if role & user_roles == role:
                    return True
            elif role in user_roles:
                return True

    def login_required(self, f=None, role=None, optional=None):
        if f is not None and \
                (role is not None or optional is not None):  # pragma: no cover
            raise ValueError(
                'role and optional are the only supported arguments')

        def login_required_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                auth = self.get_auth()

                # Flask normally handles OPTIONS requests on its own, but in
                # the case it is configured to forward those to the
                # application, we need to ignore authentication headers and
                # let the request through to avoid unwanted interactions with
                # CORS.
                if request.method != 'OPTIONS':  # pragma: no cover
                    password = self.get_auth_password(auth)

                    status = None
                    user = self.authenticate(auth, password)
                    if user in (False, None):
                        status = 401
                    elif not self.authorize(role, user, auth):
                        status = 403
                    if not optional and status:
                        try:
                            return self.auth_error_callback(status)
                        except TypeError:
                            return self.auth_error_callback()

                    g.flask_httpauth_user = user if user is not True \
                        else auth.username if auth else None
                return self.ensure_sync(f)(*args, **kwargs)
            return decorated

        if f:
            return login_required_internal(f)
        return login_required_internal

    def username(self):
        auth = self.get_auth()
        if not auth:
            return ""
        return auth.username

    def current_user(self):
        if hasattr(g, 'flask_httpauth_user'):
            return g.flask_httpauth_user

    def ensure_sync(self, f):
        try:
            return current_app.ensure_sync(f)
        except AttributeError:  # pragma: no cover
            return f


class HTTPBasicAuth(HTTPAuth):
    def __init__(self, scheme=None, realm=None):
        super(HTTPBasicAuth, self).__init__(scheme or 'Basic', realm)

        self.hash_password_callback = None
        self.verify_password_callback = None

    def hash_password(self, f):
        self.hash_password_callback = f
        return f

    def verify_password(self, f):
        self.verify_password_callback = f
        return f

    def get_auth(self):
        # this version of the Authorization header parser is more flexible
        # than Werkzeug's, as it also accepts other schemes besides "Basic"
        header = self.header or 'Authorization'
        if header not in request.headers:
            return None
        value = request.headers[header].encode('utf-8')
        try:
            scheme, credentials = value.split(b' ', 1)
            encoded_username, encoded_password = b64decode(
                credentials).split(b':', 1)
        except (ValueError, TypeError):
            return None
        try:
            username = encoded_username.decode('utf-8')
            password = encoded_password.decode('utf-8')
        except UnicodeDecodeError:
            # try to decode again with latin-1, which should always work
            username = encoded_username.decode('latin1')
            password = encoded_password.decode('latin1')

        return Authorization(
            scheme, {'username': username, 'password': password})

    def authenticate(self, auth, stored_password):
        if auth:
            username = auth.username
            client_password = auth.password
        else:
            username = ""
            client_password = ""
        if self.verify_password_callback:
            return self.ensure_sync(self.verify_password_callback)(
                username, client_password)
        if not auth:
            return
        if self.hash_password_callback:
            try:
                client_password = self.ensure_sync(
                    self.hash_password_callback)(client_password)
            except TypeError:
                client_password = self.ensure_sync(
                    self.hash_password_callback)(username, client_password)
        return auth.username if client_password is not None and \
            stored_password is not None and \
            hmac.compare_digest(client_password, stored_password) else None


class HTTPDigestAuth(HTTPAuth):
    def __init__(self, scheme=None, realm=None, use_ha1_pw=False, qop='auth',
                 algorithm='MD5'):
        super(HTTPDigestAuth, self).__init__(scheme or 'Digest', realm)
        self.use_ha1_pw = use_ha1_pw
        if isinstance(qop, str):
            self.qop = [v.strip() for v in qop.split(',')]
        else:
            self.qop = qop
        if algorithm.lower() == 'md5':
            self.algorithm = 'MD5'
        elif algorithm.lower() == 'md5-sess':
            self.algorithm = 'MD5-Sess'
        else:
            raise ValueError(f'Algorithm {algorithm} is not supported')
        self.random = SystemRandom()
        try:
            self.random.random()
        except NotImplementedError:  # pragma: no cover
            self.random = Random()

        self.generate_nonce_callback = None
        self.verify_nonce_callback = None
        self.generate_opaque_callback = None
        self.verify_opaque_callback = None

        def _generate_random():
            return md5(str(self.random.random()).encode('utf-8')).hexdigest()

        def default_generate_nonce():
            session["auth_nonce"] = _generate_random()
            return session["auth_nonce"]

        def default_verify_nonce(nonce):
            session_nonce = session.get("auth_nonce")
            if nonce is None or session_nonce is None:
                return False
            return hmac.compare_digest(nonce, session_nonce)

        def default_generate_opaque():
            session["auth_opaque"] = _generate_random()
            return session["auth_opaque"]

        def default_verify_opaque(opaque):
            session_opaque = session.get("auth_opaque")
            if opaque is None or session_opaque is None:  # pragma: no cover
                return False
            return hmac.compare_digest(opaque, session_opaque)

        self.generate_nonce(default_generate_nonce)
        self.generate_opaque(default_generate_opaque)
        self.verify_nonce(default_verify_nonce)
        self.verify_opaque(default_verify_opaque)

    def generate_nonce(self, f):
        self.generate_nonce_callback = f
        return f

    def verify_nonce(self, f):
        self.verify_nonce_callback = f
        return f

    def generate_opaque(self, f):
        self.generate_opaque_callback = f
        return f

    def verify_opaque(self, f):
        self.verify_opaque_callback = f
        return f

    def get_nonce(self):
        return self.generate_nonce_callback()

    def get_opaque(self):
        return self.generate_opaque_callback()

    def generate_ha1(self, username, password):
        a1 = username + ":" + self.realm + ":" + password
        a1 = a1.encode('utf-8')
        return md5(a1).hexdigest()

    def authenticate_header(self):
        nonce = self.get_nonce()
        opaque = self.get_opaque()
        if self.qop:
            return ('{0} realm="{1}",nonce="{2}",opaque="{3}",algorithm="{4}"'
                    ',qop="{5}"').format(
                self.scheme, self.realm, nonce,
                opaque, self.algorithm, ','.join(self.qop))
        else:
            return '{0} realm="{1}",nonce="{2}",opaque="{3}"'.format(
                self.scheme, self.realm, nonce,
                opaque)

    def authenticate(self, auth, stored_password_or_ha1):
        if not auth or not auth.username or not auth.realm or not auth.uri \
                or not auth.nonce or not auth.response \
                or not stored_password_or_ha1:
            return False
        if not(self.verify_nonce_callback(auth.nonce)) or \
                not(self.verify_opaque_callback(auth.opaque)):
            return False
        if auth.qop and auth.qop not in self.qop:  # pragma: no cover
            return False
        if self.use_ha1_pw:
            ha1 = stored_password_or_ha1
        else:
            a1 = auth.username + ":" + auth.realm + ":" + \
                stored_password_or_ha1
            ha1 = md5(a1.encode('utf-8')).hexdigest()
        if self.algorithm == 'MD5-Sess':
            ha1 = md5((ha1 + ':' + auth.nonce + ':' + auth.cnonce).encode(
                'utf-8')).hexdigest()
        a2 = request.method + ":" + auth.uri
        ha2 = md5(a2.encode('utf-8')).hexdigest()
        if auth.qop == 'auth':
            a3 = ha1 + ":" + auth.nonce + ":" + auth.nc + ":" + \
                auth.cnonce + ":auth:" + ha2
        else:
            a3 = ha1 + ":" + auth.nonce + ":" + ha2
        response = md5(a3.encode('utf-8')).hexdigest()
        return hmac.compare_digest(response, auth.response)


class HTTPTokenAuth(HTTPAuth):
    def __init__(self, scheme='Bearer', realm=None, header=None):
        super(HTTPTokenAuth, self).__init__(scheme, realm, header)

        self.verify_token_callback = None

    def verify_token(self, f):
        self.verify_token_callback = f
        return f

    def authenticate(self, auth, stored_password):
        if auth:
            token = auth['token']
        else:
            token = ""
        if self.verify_token_callback:
            return self.ensure_sync(self.verify_token_callback)(token)


class MultiAuth(object):
    def __init__(self, main_auth, *args):
        self.main_auth = main_auth
        self.additional_auth = args

    def login_required(self, f=None, role=None, optional=None):
        if f is not None and \
                (role is not None or optional is not None):  # pragma: no cover
            raise ValueError(
                'role and optional are the only supported arguments')

        def login_required_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                selected_auth = self.main_auth
                if not self.main_auth.is_compatible_auth(request.headers):
                    for auth in self.additional_auth:
                        if auth.is_compatible_auth(request.headers):
                            selected_auth = auth
                            break
                return selected_auth.login_required(
                    role=role, optional=optional)(f)(*args, **kwargs)
            return decorated

        if f:
            return login_required_internal(f)
        return login_required_internal

    def current_user(self):
        if hasattr(g, 'flask_httpauth_user'):  # pragma: no cover
            return g.flask_httpauth_user
