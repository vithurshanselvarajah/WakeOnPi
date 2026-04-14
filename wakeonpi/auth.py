from functools import wraps
from flask import request, Response
from . import config


def check_auth(username, password):
    s = config.current_settings()
    return username == s.get('HTTP_USERNAME') and password == s.get('HTTP_PASSWORD')


def authenticate():
    return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated