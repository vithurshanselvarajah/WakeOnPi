import unittest
from unittest.mock import patch
from wakeonpi import camera, state


class TestCameraInterface(unittest.TestCase):

    def setUp(self):
        # Reset state flags
        state.main_stream_active = False
        state.clients_connected = 0
        state.ignore_motion_until = 0
        state.motion_prev_frame_stale = False

    def test_camera_module_import(self):
        self.assertIsNotNone(camera)

    def test_camera_has_implementation(self):
        self.assertTrue(len(dir(camera)) > 0)

    @patch('wakeonpi.camera.picam2')
    def test_capture_lores(self, mock_picam2):
        mock_picam2.capture_array.return_value = "lores_frame"
        frame = camera.capture_lores()
        self.assertEqual(frame, "lores_frame")
        mock_picam2.capture_array.assert_called_once_with("lores")

    @patch('wakeonpi.camera.picam2')
    def test_capture_main(self, mock_picam2):
        mock_picam2.capture_array.return_value = "main_frame"
        frame = camera.capture_main()
        self.assertEqual(frame, "main_frame")
        mock_picam2.capture_array.assert_called_once_with("main")

    @patch('wakeonpi.camera.picam2')
    def test_switch_to_full_mode(self, mock_picam2):
        # Initially inactive
        state.main_stream_active = False
        state.motion_prev_frame_stale = False

        camera.switch_to_full_mode()

        self.assertTrue(state.main_stream_active)
        self.assertTrue(state.motion_prev_frame_stale)
        self.assertGreater(state.ignore_motion_until, 0)
        mock_picam2.switch_mode.assert_called_once()

    @patch('wakeonpi.camera.picam2')
    def test_switch_to_lores_mode_if_needed(self, mock_picam2):
        # Active, client count 0
        state.main_stream_active = True
        state.clients_connected = 0
        state.motion_prev_frame_stale = False

        camera.switch_to_lores_mode_if_needed()

        self.assertFalse(state.main_stream_active)
        self.assertTrue(state.motion_prev_frame_stale)
        mock_picam2.switch_mode.assert_called_once_with(camera.video_config_lores)


if __name__ == '__main__':
    unittest.main()

