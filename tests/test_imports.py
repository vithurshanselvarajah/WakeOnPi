import unittest
import sys
from unittest.mock import MagicMock

sys.modules['cv2'] = MagicMock()
sys.modules['picamera2'] = MagicMock()
sys.modules['picamera2.picamera'] = MagicMock()


class TestPackageImports(unittest.TestCase):

    def test_import_wakeonpi_package(self):
        import wakeonpi
        self.assertIsNotNone(wakeonpi)

    def test_import_config_module(self):
        from wakeonpi import config
        self.assertIsNotNone(config)

    def test_import_app_module(self):
        from wakeonpi import app
        self.assertIsNotNone(app)

    def test_import_auth_module(self):
        from wakeonpi import auth
        self.assertIsNotNone(auth)

    def test_import_motion_module(self):
        from wakeonpi import motion
        self.assertIsNotNone(motion)

    def test_import_display_module(self):
        from wakeonpi import display
        self.assertIsNotNone(display)

    def test_import_camera_module(self):
        from wakeonpi import camera
        self.assertIsNotNone(camera)

    def test_import_mqtt_module(self):
        from wakeonpi import mqtt
        self.assertIsNotNone(mqtt)

    def test_import_recorder_module(self):
        from wakeonpi import recorder
        self.assertIsNotNone(recorder)

    def test_import_state_module(self):
        from wakeonpi import state
        self.assertIsNotNone(state)

    def test_import_system_module(self):
        from wakeonpi import system
        self.assertIsNotNone(system)

    def test_import_logging_config_module(self):
        from wakeonpi import logging_config
        self.assertIsNotNone(logging_config)


if __name__ == '__main__':
    unittest.main()
