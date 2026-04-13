import os
from flask import request, Response

from . import config


def check_auth(username, password):
    s = config.current_settings()
    expected_user = s.get('HTTP_USERNAME')
    expected_pass = s.get('HTTP_PASSWORD')
    return username == expected_user and password == expected_pass


def authenticate():
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )


def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    decorated.__name__ = f.__name__
    return decorated