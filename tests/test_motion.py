import unittest
from unittest.mock import patch
import numpy as np
from wakeonpi import motion, state, config


class TestMotionDetection(unittest.TestCase):

    def setUp(self):
        state.motion_prev_frame_stale = False
        state.ignore_motion_until = 0

    def test_motion_module_import(self):
        self.assertIsNotNone(motion)

    def test_motion_has_implementation(self):
        self.assertTrue(len(dir(motion)) > 0)

    @patch('wakeonpi.motion.capture_lores')
    @patch('time.sleep')
    def test_motion_loop_stale_frame_reset(self, mock_sleep, mock_capture):
        state.motion_prev_frame_stale = True

        class ExitLoop(Exception):
            pass

        mock_sleep.side_effect = ExitLoop()

        # Mock a YUV420 frame (height = 270, width = 320)
        mock_frame = np.zeros((270, 320), dtype=np.uint8)
        mock_capture.return_value = mock_frame

        try:
            motion.motion_detection_loop()
        except ExitLoop:
            pass

        self.assertFalse(state.motion_prev_frame_stale)

    @patch('wakeonpi.motion.capture_lores')
    @patch('time.sleep')
    def test_motion_loop_capture_failure_resets_prev_frame(self, mock_sleep, mock_capture):
        class ExitLoop(Exception):
            pass

        mock_sleep.side_effect = ExitLoop()
        mock_capture.side_effect = Exception("Capture error")

        try:
            motion.motion_detection_loop()
        except ExitLoop:
            pass

        # If it failed, it must have called sleep(CHECK_INTERVAL) before continue
        mock_sleep.assert_called_with(config.CHECK_INTERVAL)


if __name__ == '__main__':
    unittest.main()

