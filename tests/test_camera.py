import sys
import types
import importlib

picam_mod = types.ModuleType('picamera2')
class Picamera2:
    def __init__(self):
        self.mode = None
    def create_video_configuration(self, **k):
        return {'cfg': True}
    def configure(self, cfg):
        pass
    def start(self):
        pass
    def switch_mode(self, cfg):
        self.mode = cfg
    def capture_array(self, name):
        try:
            import numpy as np
            return np.zeros((180, 320), dtype='uint8')
        except Exception:
            class A:
                shape = (180, 320)
                def copy(self):
                    return self
            return A()
picam_mod.Picamera2 = Picamera2
libcamera_mod = types.ModuleType('libcamera')
class Transform:
    def __init__(self, **k):
        pass
libcamera_mod.Transform = Transform
sys.modules['picamera2'] = picam_mod
sys.modules['libcamera'] = libcamera_mod

import wakeonpi.camera as camera
import wakeonpi.state as state


def test_switch_modes(monkeypatch):
    # ensure state
    state.main_stream_active = False
    state.clients_connected = 0
    camera.switch_to_full_mode()
    assert state.main_stream_active is True
    state.clients_connected = 0
    camera.switch_to_lores_mode_if_needed()
    assert state.main_stream_active is False
