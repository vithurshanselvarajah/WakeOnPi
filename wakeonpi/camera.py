import time
from picamera2 import Picamera2
from libcamera import Transform
from . import state

picam2 = Picamera2()

video_config_lores = picam2.create_video_configuration(
    lores={"size": (320, 180), "format": "YUV420"},
    transform=Transform(vflip=True),
    controls={"FrameRate": 2, "AwbMode": 0}
)

video_config_full = picam2.create_video_configuration(
    main={"size": (1920, 1080), "format": "RGB888"},
    lores={"size": (320, 180), "format": "YUV420"},
    transform=Transform(vflip=True),
    controls={"FrameRate": 10, "AwbMode": 0}
)

picam2.configure(video_config_lores)
picam2.start()


def switch_to_full_mode():
    with state.main_stream_lock:
        if not state.main_stream_active:
            state.ignore_motion_until = time.time() + 2
            picam2.switch_mode(video_config_full)
            state.main_stream_active = True


def switch_to_lores_mode_if_needed():
    with state.main_stream_lock:
        if state.main_stream_active and state.clients_connected == 0:
            state.ignore_motion_until = time.time() + 2
            picam2.switch_mode(video_config_lores)
            state.main_stream_active = False