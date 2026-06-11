import unittest
from unittest.mock import patch
from wakeonpi import app, state, config, updater


class TestAppIntegration(unittest.TestCase):

    def setUp(self):
        # Configure app for testing
        app.app.config['TESTING'] = True
        app.app.secret_key = "test_secret_key"
        self.client = app.app.test_client()

        # Ensure setup complete is true for requires_session_auth
        config.update_settings(SETUP_COMPLETE=True)

        # Authenticate session
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True

    def test_app_module_import(self):
        self.assertIsNotNone(app.app)

    @patch('wakeonpi.updater.updater_instance')
    @patch('wakeonpi.updater.check_for_updates')
    @patch('wakeonpi.mqtt._get_version')
    def test_settings_update_get(self, mock_get_ver, mock_check, mock_updater):
        mock_get_ver.return_value = "0.0.10"
        state.latest_version = "0.0.11"
        mock_updater.fetch_release_notes.return_value = "Bug fixes and improvements"

        resp = self.client.get("/settings/update")
        self.assertEqual(resp.status_code, 200)

        html = resp.data.decode()
        self.assertIn("v0.0.10", html)
        self.assertIn("v0.0.11", html)
        self.assertIn("Bug fixes and improvements", html)

    @patch('wakeonpi.updater.trigger_update')
    def test_settings_update_post(self, mock_trigger):
        state.update_status = "idle"

        resp = self.client.post("/settings/update")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json, {"success": True})
        mock_trigger.assert_called_once_with(triggered_by="webui")

    @patch('wakeonpi.updater.trigger_update')
    def test_settings_update_post_in_progress(self, mock_trigger):
        state.update_status = "installing"

        resp = self.client.post("/settings/update")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json)
        mock_trigger.assert_not_called()

    @patch('wakeonpi.mqtt._get_version')
    def test_settings_rollback_get(self, mock_get_ver):
        mock_get_ver.return_value = "0.0.11"
        state.installed_versions = ["0.0.10", "0.0.11"]
        state.current_version = "0.0.11"

        resp = self.client.get("/settings/rollback")
        self.assertEqual(resp.status_code, 200)

        html = resp.data.decode()
        self.assertIn("v0.0.10", html)
        self.assertIn("v0.0.11", html)

    @patch('wakeonpi.updater.updater_instance')
    def test_settings_rollback_post(self, mock_updater):
        resp = self.client.post("/settings/rollback", data={"version": "0.0.10"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json, {"success": True})
        mock_updater.rollback.assert_called_once_with("0.0.10", restart_callback=updater.restart_process)

    @patch('wakeonpi.updater.updater_instance')
    def test_settings_rollback_post_failure(self, mock_updater):
        mock_updater.rollback.side_effect = Exception("Rollback error")

        resp = self.client.post("/settings/rollback", data={"version": "0.0.10"})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json, {"success": False, "error": "Rollback failed"})

    @patch('wakeonpi.db.reset_db')
    def test_settings_db_reset_post(self, mock_reset):
        resp = self.client.post("/settings/db/reset")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/settings", resp.headers["Location"])
        mock_reset.assert_called_once()


if __name__ == '__main__':
    unittest.main()
