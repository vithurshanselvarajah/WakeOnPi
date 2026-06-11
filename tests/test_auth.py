import unittest
import base64
from flask import Flask
from wakeonpi import auth, config, db


class TestAuthentication(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "test_secret_key"
        self.app.config['SERVER_NAME'] = 'localhost:5000'

        self.pwd_hash = db.hash_password("password")
        config.update_settings(
            HTTP_USERNAME="admin",
            HTTP_PASSWORD_HASH=self.pwd_hash,
            STREAM_USERNAME="stream_user",
            STREAM_PASSWORD="stream_password",
            SETUP_COMPLETE=True
        )

    def test_check_auth(self):
        self.assertTrue(auth.check_auth("admin", "password"))
        self.assertFalse(auth.check_auth("admin", "wrongpassword"))
        self.assertFalse(auth.check_auth("wronguser", "password"))

    def test_check_stream_auth(self):
        self.assertTrue(auth.check_stream_auth("stream_user", "stream_password"))
        self.assertFalse(auth.check_stream_auth("stream_user", "wrong"))
        self.assertFalse(auth.check_stream_auth("wrong", "stream_password"))

    def test_requires_session_auth_decorator_redirect_setup(self):
        config.update_settings(SETUP_COMPLETE=False)

        @self.app.route("/protected")
        @auth.requires_session_auth
        def protected_route():
            return "success"

        @self.app.route("/setup")
        def setup():
            return "setup_page"

        client = self.app.test_client()

        with self.app.app_context():
            resp = client.get("/protected")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/setup", resp.headers["Location"])

    def test_requires_session_auth_decorator_redirect_login(self):
        config.update_settings(SETUP_COMPLETE=True)

        @self.app.route("/protected2")
        @auth.requires_session_auth
        def protected_route():
            return "success"

        @self.app.route("/login")
        def login():
            return "login_page"

        client = self.app.test_client()

        with self.app.app_context():
            resp = client.get("/protected2")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login", resp.headers["Location"])

        with client.session_transaction() as sess:
            sess["logged_in"] = True

        resp = client.get("/protected2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode(), "success")

    def test_requires_stream_auth_decorator(self):
        config.update_settings(SETUP_COMPLETE=True)

        @self.app.route("/stream_protected")
        @auth.requires_stream_auth
        def stream_route():
            return "stream_success"

        client = self.app.test_client()

        resp = client.get("/stream_protected")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("WWW-Authenticate", resp.headers)

        with client.session_transaction() as sess:
            sess["logged_in"] = True
        resp = client.get("/stream_protected")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode(), "stream_success")

        with client.session_transaction() as sess:
            sess["logged_in"] = False

        headers = {
            "Authorization": "Basic " + base64.b64encode(b"stream_user:stream_password").decode("utf-8")
        }
        resp = client.get("/stream_protected", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.decode(), "stream_success")

        headers = {
            "Authorization": "Basic " + base64.b64encode(b"stream_user:wrong_pass").decode("utf-8")
        }
        resp = client.get("/stream_protected", headers=headers)
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
