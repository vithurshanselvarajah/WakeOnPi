from . import app, auth, camera, config, display, motion, mqtt, state

import sys
import types

if 'libcamera' not in sys.modules:
    _libcamera = types.ModuleType('libcamera')
    class Transform:
        def __init__(self, *args, **kwargs):
            pass
    _libcamera.Transform = Transform
    sys.modules['libcamera'] = _libcamera

if 'picamera2' not in sys.modules:
    _picam = types.ModuleType('picamera2')
    class Picamera2:
        def __init__(self):
            self._mode = None
        def create_video_configuration(self, **kwargs):
            return {'lores': True}
        def configure(self, cfg):
            pass
        def start(self):
            pass
        def switch_mode(self, cfg):
            self._mode = cfg
        def capture_array(self, name):
            class Arr:
                shape = (180, 320)
                def copy(self):
                    return self
                def __getitem__(self, idx):
                    return self
            return Arr()
    _picam.Picamera2 = Picamera2
    sys.modules['picamera2'] = _picam

__all__ = ["app", "auth", "camera", "config", "display", "motion", "mqtt", "state"]