import unittest
from pathlib import Path
from wakeonpi import config


class TestConfiguration(unittest.TestCase):

    def test_config_module_import(self):
        self.assertIsNotNone(config)

    def test_config_has_implementation(self):
        self.assertTrue(len(dir(config)) > 0)

    def test_config_loads_from_template(self):
        self.assertIn("MOTION_THRESHOLD", config.DEFAULTS)
        self.assertIn("HTTP_USERNAME", config.DEFAULTS)
        # Verify that HTTP_USERNAME default has been removed (set to None)
        self.assertIsNone(config.DEFAULTS["HTTP_USERNAME"])

    def test_config_resolves_recordings_root(self):
        # Verify RECORDINGS_ROOT is resolved to an absolute path
        recordings_root = config.DEFAULTS["RECORDINGS_ROOT"]
        self.assertTrue(Path(recordings_root).is_absolute())
        self.assertTrue(recordings_root.endswith("recordings"))


if __name__ == '__main__':
    unittest.main()
