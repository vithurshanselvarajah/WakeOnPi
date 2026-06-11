import unittest
import json
import tempfile
import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from wakeonpi import updater, state
from wakeonpi.github_updater import GitHubReleaseUpdater


class TestUpdater(unittest.TestCase):

    @patch('urllib.request.urlopen')
    def test_fetch_latest_version_toml(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'version = "0.0.99"\nname = "WakeOnPi"'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        version = updater.fetch_latest_version()
        self.assertEqual(version, "0.0.99")

    @patch('urllib.request.urlopen')
    def test_fetch_latest_version_fallback(self, mock_urlopen):
        def mock_urlopen_side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else req
            if "pyproject.toml" in url:
                raise Exception("Raw 404")
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"tag_name": "v0.0.100"}'
            mock_response.__enter__.return_value = mock_response
            return mock_response

        mock_urlopen.side_effect = mock_urlopen_side_effect

        version = updater.fetch_latest_version()
        self.assertEqual(version, "0.0.100")

    @patch('wakeonpi.updater.fetch_latest_version')
    def test_check_for_updates(self, mock_fetch):
        mock_fetch.return_value = "0.0.100"

        latest = updater.check_for_updates()
        self.assertEqual(latest, "0.0.100")
        self.assertEqual(state.latest_version, "0.0.100")
        self.assertEqual(state.update_status, "idle")

        mock_fetch.return_value = None
        latest = updater.check_for_updates()
        self.assertIsNone(latest)
        self.assertEqual(state.update_status, "failed")
        self.assertIsNotNone(state.update_error)

    @patch('os.execv')
    @patch('sys.exit')
    def test_restart_process(self, mock_exit, mock_execv):
        updater.restart_process()
        mock_execv.assert_called_once()

        mock_execv.side_effect = Exception("Fail")
        updater.restart_process()
        mock_exit.assert_called_with(1)

    @patch('wakeonpi.updater.updater_instance')
    @patch('wakeonpi.updater.restart_process')
    def test_update_worker_success(self, mock_restart, mock_updater):
        state.update_status = "idle"
        mock_updater.fetch_latest_release.return_value = "0.0.100"

        updater._update_worker()

        self.assertEqual(state.update_status, "idle")
        mock_updater.fetch_latest_release.assert_called_once()
        mock_updater.install_release.assert_called_once_with("0.0.100")
        mock_restart.assert_called_once()

    @patch('wakeonpi.updater.updater_instance')
    @patch('wakeonpi.updater.restart_process')
    def test_update_worker_failure(self, mock_restart, mock_updater):
        state.update_status = "idle"
        mock_updater.fetch_latest_release.side_effect = Exception("Download failed")

        updater._update_worker()

        self.assertEqual(state.update_status, "failed")
        self.assertEqual(state.update_error, "Download failed")
        mock_restart.assert_not_called()


class TestGitHubReleaseUpdater(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        # Mock load_manifest inside constructor by patching Path
        with patch('wakeonpi.github_updater.Path') as mock_path:
            # We want Path(__file__).parent / "updates" to point to self.temp_path
            mock_path.return_value.parent.__truediv__.return_value = self.temp_path
            self.updater = GitHubReleaseUpdater()

        # Ensure updates_dir and manifest_path are set to temp folder directly
        self.updater.updates_dir = self.temp_path
        self.updater.manifest_path = self.temp_path / "manifest.json"
        state.installed_versions = []
        state.current_version = ""

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_manifest_load_save(self):
        state.installed_versions = ["0.0.1", "0.0.2"]
        state.current_version = "0.0.2"
        self.updater._save_manifest()

        # Reset states and reload
        state.installed_versions = []
        state.current_version = ""
        self.updater._load_manifest()

        self.assertEqual(state.installed_versions, ["0.0.1", "0.0.2"])
        self.assertEqual(state.current_version, "0.0.2")

    @patch('urllib.request.urlopen')
    def test_fetch_latest_release(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v0.0.15"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        tag = self.updater.fetch_latest_release(triggered_by="home_assistant")
        self.assertEqual(tag, "0.0.15")
        self.assertEqual(state.latest_version, "0.0.15")
        self.assertEqual(state.update_initiated_by, "home_assistant")

    @patch('urllib.request.urlretrieve')
    @patch('urllib.request.urlopen')
    def test_download_release(self, mock_urlopen, mock_urlretrieve):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "assets": [
                {"name": "wakeonpi-0.0.15.zip", "browser_download_url": "http://zip"},
                {"name": "wakeonpi-0.0.15.zip.sha256", "browser_download_url": "http://sha"}
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        zip_path = self.updater.download_release("0.0.15")
        self.assertEqual(zip_path.name, "wakeonpi-0.0.15.zip")
        self.assertTrue(zip_path.parent.exists())
        self.assertEqual(mock_urlretrieve.call_count, 2)

    def test_verify_checksum_success(self):
        zip_path = self.temp_path / "wakeonpi-0.0.15.zip"
        zip_path.write_text("dummy content")

        sha256 = hashlib.sha256(b"dummy content").hexdigest()
        checksum_path = self.temp_path / "wakeonpi-0.0.15.zip.sha256"
        checksum_path.write_text(f"{sha256}  wakeonpi-0.0.15.zip")

        # Should not raise exception
        self.updater.verify_checksum(zip_path)

    def test_verify_checksum_mismatch(self):
        zip_path = self.temp_path / "wakeonpi-0.0.15.zip"
        zip_path.write_text("dummy content")

        checksum_path = self.temp_path / "wakeonpi-0.0.15.zip.sha256"
        checksum_path.write_text("wrongsha  wakeonpi-0.0.15.zip")

        with self.assertRaises(RuntimeError) as ctx:
            self.updater.verify_checksum(zip_path)
        self.assertIn("Checksum mismatch", str(ctx.exception))

    @patch('wakeonpi.github_updater.GitHubReleaseUpdater.download_release')
    @patch('wakeonpi.github_updater.GitHubReleaseUpdater.verify_checksum')
    def test_install_release(self, mock_verify, mock_download):
        tag = "0.0.15"
        tmp_subdir = self.temp_path / f"tmp_{tag}"
        tmp_subdir.mkdir(exist_ok=True)
        zip_path = tmp_subdir / f"wakeonpi-{tag}.zip"

        # Create a mock zip containing one file
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "content")

        mock_download.return_value = zip_path

        self.updater.install_release(tag)

        self.assertEqual(state.current_version, tag)
        self.assertIn(tag, state.installed_versions)
        # Check that test.txt exists in updates/0.0.15
        installed_txt = self.temp_path / tag / "test.txt"
        self.assertTrue(installed_txt.exists())
        self.assertEqual(installed_txt.read_text(), "content")
        # Check that temp folder was cleaned up
        self.assertFalse(tmp_subdir.exists())

    @patch('wakeonpi.updater.restart_process')
    def test_rollback(self, mock_restart):
        state.installed_versions = ["0.0.14", "0.0.15"]
        state.current_version = "0.0.15"

        self.updater.rollback("0.0.14", restart_callback=updater.restart_process)
        self.assertEqual(state.current_version, "0.0.14")
        mock_restart.assert_called_once()

    def test_prune_versions(self):
        state.installed_versions = ["0.0.14", "0.0.15"]
        v14_path = self.temp_path / "0.0.14"
        v15_path = self.temp_path / "0.0.15"
        v14_path.mkdir()
        v15_path.mkdir()

        self.updater.prune_versions(except_tag="0.0.15")

        self.assertEqual(state.installed_versions, ["0.0.15"])
        self.assertFalse(v14_path.exists())
        self.assertTrue(v15_path.exists())


if __name__ == '__main__':
    unittest.main()
