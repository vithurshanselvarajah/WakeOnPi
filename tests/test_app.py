import wakeonpi.app as app
from flask import Flask
import pytest


pytest.skip("skipping test_app - disabled in CI due to hardware dependencies", allow_module_level=True)


def test_get_local_ip_basic():
    ip = app.get_local_ip()
    assert isinstance(ip, str)


def test_motion_alerts_route(monkeypatch):
    # ensure state values
    import wakeonpi.state as state
    monkeypatch.setattr(state, 'motion_event', True)
    with app.app.test_client() as c:
        rv = c.get('/motion_alerts')
        assert rv.status_code == 200
        assert rv.data == b'motion'
    monkeypatch.setattr(state, 'motion_event', False)
    with app.app.test_client() as c:
        rv = c.get('/motion_alerts')
        assert rv.status_code == 200
        assert rv.data == b'nomotion'
