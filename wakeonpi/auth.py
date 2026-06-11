from functools import wraps
from flask import request, Response, session, redirect, url_for
from . import config, db


def check_auth(username, password):
    s = config.current_settings()
    correct_username = s.get("HTTP_USERNAME")
    pwd_hash = s.get("HTTP_PASSWORD_HASH")
    return username == correct_username and db.verify_password(password, pwd_hash)


def check_stream_auth(username, password):
    s = config.current_settings()
    return username == s.get("STREAM_USERNAME", "stream") and password == s.get("STREAM_PASSWORD")


def authenticate_stream():
    return Response(
        "Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Stream Login Required"'}
    )


def requires_session_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not config.SETUP_COMPLETE:
            return redirect(url_for("setup"))
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated


def requires_stream_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not config.SETUP_COMPLETE:
            return f(*args, **kwargs)
        if session.get("logged_in"):
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_stream_auth(auth.username, auth.password):
            return authenticate_stream()
        return f(*args, **kwargs)

    return decorated
