import time
import logging
import threading
from picamera2 import Picamera2
from libcamera import Transform
from . import state, config

log = logging.getLogger("Camera")

picam2 = Picamera2()

# This lock protects ALL picam2 operations: mode switches, capture_array calls,
# and reconfigure calls. Any code touching the camera must hold this lock.
camera_lock = threading.Lock()


def _get_stream_resolution():
    try:
        res = config.current_settings().get("STREAM_RESOLUTION") or "854x480"
        w, h = res.lower().split("x")
        return (int(w), int(h))
    except Exception:
        return (854, 480)


def _get_stream_fps():
    try:
        return int(config.current_settings().get("STREAM_FPS") or 10)
    except Exception:
        return 10


def _get_stream_quality():
    try:
        return int(config.current_settings().get("STREAM_QUALITY") or 75)
    except Exception:
        return 75


def create_lores_config():
    return picam2.create_video_configuration(
        lores={"size": (320, 180), "format": "YUV420"},
        transform=Transform(vflip=True),
        controls={"FrameRate": 2, "AwbMode": 0},
    )


def create_full_config():
    fps = _get_stream_fps()
    return picam2.create_video_configuration(
        main={"size": (1920, 1080), "format": "RGB888"},
        lores={"size": (320, 180), "format": "YUV420"},
        transform=Transform(vflip=True),
        controls={"FrameRate": fps, "AwbMode": 0},
    )


video_config_lores = create_lores_config()
video_config_full = create_full_config()

picam2.configure(video_config_lores)
picam2.start()


def switch_to_full_mode():
    global video_config_full
    with camera_lock:
        if not state.main_stream_active:
            state.ignore_motion_until = time.time() + 2
            state.motion_prev_frame_stale = True
            video_config_full = create_full_config()
            picam2.switch_mode(video_config_full)
            state.main_stream_active = True


def switch_to_lores_mode_if_needed():
    with camera_lock:
        if state.main_stream_active and state.clients_connected == 0:
            state.ignore_motion_until = time.time() + 2
            state.motion_prev_frame_stale = True
            picam2.switch_mode(video_config_lores)
            state.main_stream_active = False


def capture_lores():
    """Thread-safe capture of a lores frame for motion detection."""
    with camera_lock:
        return picam2.capture_array("lores")


def capture_main():
    """Thread-safe capture of a main (full-res) frame for streaming/recording."""
    with camera_lock:
        return picam2.capture_array("main")


def get_stream_settings():
    return {
        "resolution": _get_stream_resolution(),
        "fps": _get_stream_fps(),
        "quality": _get_stream_quality(),
    }


def reconfigure():
    global video_config_lores, video_config_full
    video_config_lores = create_lores_config()
    video_config_full = create_full_config()
    with camera_lock:
        state.motion_prev_frame_stale = True
        if state.main_stream_active:
            picam2.switch_mode(video_config_full)
        else:
            picam2.switch_mode(video_config_lores)
