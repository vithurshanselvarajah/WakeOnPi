import os
from flask import request, Response

from . import config

USERNAME = getattr(config, "HTTP_USERNAME")
PASSWORD = getattr(config, "HTTP_PASSWORD")


def check_auth(username, password):
    return username == USERNAME and password == PASSWORD


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