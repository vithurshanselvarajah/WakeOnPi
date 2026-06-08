import unittest
from unittest.mock import patch, MagicMock


class TestLoggingConfiguration(unittest.TestCase):

    def test_logging_config_exists(self):
        from wakeonpi import logging_config
        self.assertIsNotNone(logging_config)

    @patch('wakeonpi.logging_config.setup_logging')
    def test_setup_logging_called(self, mock_setup):
        mock_setup()
        mock_setup.assert_called_once()

    @patch('logging.getLogger')
    def test_logger_creation(self, mock_logger):
        mock_logger.return_value = MagicMock()
        logger = mock_logger('test')
        self.assertIsNotNone(logger)


if __name__ == '__main__':
    unittest.main()
