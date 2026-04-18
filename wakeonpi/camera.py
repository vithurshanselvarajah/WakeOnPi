import time
import logging
from picamera2 import Picamera2
from libcamera import Transform
from . import state, config

log = logging.getLogger("Camera")

picam2 = Picamera2()

def _get_stream_resolution():
    try:
        res = config.STREAM_RESOLUTION or "854x480"
        w, h = res.lower().split("x")
        return (int(w), int(h))
    except Exception:
        return (854, 480)

def _get_stream_fps():
    try:
        return int(config.STREAM_FPS or 10)
    except Exception:
        return 10

def _get_stream_quality():
    try:
        return int(config.STREAM_QUALITY or 75)
    except Exception:
        return 75

def create_lores_config():
    return picam2.create_video_configuration(
        lores={"size": (320, 180), "format": "YUV420"},
        transform=Transform(vflip=True),
        controls={"FrameRate": 2, "AwbMode": 0}
    )

def create_full_config():
    fps = _get_stream_fps()
    return picam2.create_video_configuration(
        main={"size": (1920, 1080), "format": "RGB888"},
        lores={"size": (320, 180), "format": "YUV420"},
        transform=Transform(vflip=True),
        controls={"FrameRate": fps, "AwbMode": 0}
    )

video_config_lores = create_lores_config()
video_config_full = create_full_config()

picam2.configure(video_config_lores)
picam2.start()


def switch_to_full_mode():
    global video_config_full
    with state.main_stream_lock:
        if not state.main_stream_active:
            state.ignore_motion_until = time.time() + 2
            video_config_full = create_full_config()
            picam2.switch_mode(video_config_full)
            state.main_stream_active = True


def switch_to_lores_mode_if_needed():
    with state.main_stream_lock:
        if state.main_stream_active and state.clients_connected == 0:
            state.ignore_motion_until = time.time() + 2
            picam2.switch_mode(video_config_lores)
            state.main_stream_active = False


def get_stream_settings():
    return {
        "resolution": _get_stream_resolution(),
        "fps": _get_stream_fps(),
        "quality": _get_stream_quality()
    }


def reconfigure():
    global video_config_lores, video_config_full
    video_config_lores = create_lores_config()
    video_config_full = create_full_config()
    if state.main_stream_active:
        picam2.switch_mode(video_config_full)
    else:
        picam2.switch_mode(video_config_lores)