import os
import types
from flask import Response
import pytest

import wakeonpi.auth as auth

pytest.skip("skipping test_auth - disabled in CI due to hardware-related import issues", allow_module_level=True)


def test_check_auth_env(monkeypatch):
    monkeypatch.setenv('MOTION_USERNAME', 'user')
    monkeypatch.setenv('MOTION_PASSWORD', 'pass')
    importlib = __import__('importlib')
    importlib.reload(auth)
    assert auth.check_auth('user', 'pass')
    assert not auth.check_auth('x', 'y')


def test_authenticate_response():
    r = auth.authenticate()
    assert isinstance(r, Response)
    assert r.status_code == 401
    assert 'WWW-Authenticate' in r.headers
