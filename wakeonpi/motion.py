import time
import threading
import cv2

from . import state, config
from .camera import picam2
from .display import set_display
from . import mqtt

def motion_detection_loop():
    prev_frame = None

    state.manual_display_override = False

    def set_display_if_needed(val):
        if val != state.display_on:
            set_display(val)
            state.display_on = val
            mqtt.publish_display(val)

    while True:
        lores_frame = picam2.capture_array("lores")
        gray = lores_frame[: lores_frame.shape[0] // 3, :].copy()
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if prev_frame is not None and time.time() > state.ignore_motion_until:
            delta = cv2.absdiff(prev_frame, gray)
            _, thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
            motion_score = cv2.countNonZero(thresh)

            is_motion = motion_score > config.MOTION_THRESHOLD

            if state.manual_display_override:
                prev_frame = gray
                time.sleep(60)
                continue

            if is_motion:
                state.last_motion_time = time.time()
                set_display_if_needed(True)
                if not state.motion_event:
                    state.motion_event = True
                    mqtt.publish_motion(True)

            elif time.time() - state.last_motion_time > config.INACTIVITY_TIMEOUT:
                set_display_if_needed(False)
                if state.motion_event:
                    state.motion_event = False
                    mqtt.publish_motion(False)

        prev_frame = gray
        time.sleep(config.CHECK_INTERVAL)
_motion_thread = None
_motion_thread_lock = threading.Lock()

def start_motion_thread():
    global _motion_thread
    with _motion_thread_lock:
        if _motion_thread is not None and _motion_thread.is_alive():
            return
        _motion_thread = threading.Thread(target=motion_detection_loop, daemon=True)
        _motion_thread.start()