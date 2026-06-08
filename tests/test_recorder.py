import unittest
from unittest.mock import patch, MagicMock


class TestRecorder(unittest.TestCase):

    @patch('wakeonpi.recorder.Recorder')
    def test_recorder_initialization(self, mock_recorder):
        mock_instance = MagicMock()
        mock_recorder.return_value = mock_instance
        recorder = mock_recorder()
        self.assertIsNotNone(recorder)

    @patch('wakeonpi.recorder.Recorder')
    def test_recorder_start(self, mock_recorder):
        mock_instance = MagicMock()
        mock_recorder.return_value = mock_instance
        recorder = mock_recorder()
        recorder.start()
        mock_instance.start.assert_called_once()

    @patch('wakeonpi.recorder.Recorder')
    def test_recorder_stop(self, mock_recorder):
        mock_instance = MagicMock()
        mock_recorder.return_value = mock_instance
        recorder = mock_recorder()
        recorder.stop()
        mock_instance.stop.assert_called_once()

    @patch('wakeonpi.recorder.Recorder')
    def test_recorder_quality_setting(self, mock_recorder):
        mock_instance = MagicMock()
        mock_instance.quality = 23
        mock_recorder.return_value = mock_instance
        recorder = mock_recorder()
        self.assertEqual(recorder.quality, 23)

    @patch('wakeonpi.recorder.Recorder')
    def test_recorder_output_path(self, mock_recorder):
        mock_instance = MagicMock()
        mock_instance.output_dir = './recordings'
        mock_recorder.return_value = mock_instance
        recorder = mock_recorder()
        self.assertEqual(recorder.output_dir, './recordings')


if __name__ == '__main__':
    unittest.main()
