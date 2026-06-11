import sys
from unittest.mock import MagicMock

cv2_mock = MagicMock()
cv2_mock.threshold.return_value = (0, MagicMock())
cv2_mock.countNonZero.return_value = 0
sys.modules['cv2'] = cv2_mock

sys.modules['picamera2'] = MagicMock()
sys.modules['picamera2.picamera'] = MagicMock()
sys.modules['libcamera'] = MagicMock()
sys.modules['libcamera.controls'] = MagicMock()
sys.modules['prctl'] = MagicMock()
