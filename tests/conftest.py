import sys
from unittest.mock import MagicMock

sys.modules['cv2'] = MagicMock()
sys.modules['picamera2'] = MagicMock()
sys.modules['picamera2.picamera'] = MagicMock()
sys.modules['libcamera'] = MagicMock()
sys.modules['libcamera.controls'] = MagicMock()
sys.modules['prctl'] = MagicMock()
