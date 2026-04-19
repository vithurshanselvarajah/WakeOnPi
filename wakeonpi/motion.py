import time
import threading
import cv2
import logging

from . import state, config, mqtt, browser
from .camera import picam2
from .display import set_display

log = logging.getLogger("Motion")
_motion_thread = None
_motion_thread_lock = threading.Lock()
_motion_recording_stop_time = 0


def _set_display_if_needed(val):
    mode = config.current_settings().get("SCREEN_CONTROL_MODE", "auto")
    if mode != "auto":
        return
    if val != state.display_on:
        set_display(val)
        state.display_on = val
        mqtt.publish_display(val)
        if val:
            override = getattr(state, "browser_override_url", None)
            if override:
                try:
                    browser.show_url(override, force=True)
                except Exception:
                    log.exception("Error controlling browser")


def _handle_motion_recording(is_motion):
    global _motion_recording_stop_time
    settings = config.current_settings()
    if not settings.get("RECORD_ON_MOTION", False):
        return
    if not settings.get("RECORDING_ENABLED", True):
        return
    if not settings.get("CAMERA_ENABLED", True):
        return
    try:
        from . import recorder
        post_timeout = settings.get("RECORD_POST_MOTION_TIMEOUT", 10)
        if is_motion:
            _motion_recording_stop_time = time.time() + post_timeout
            if not recorder.is_recording():
                if _check_storage_for_recording():
                    ok, path = recorder.start_recording(config.RECORDINGS_ROOT)
                    if ok:
                        log.info(f"Started motion recording: {path}")
                        mqtt.publish_recording_state(True)
        else:
            if recorder.is_recording() and time.time() > _motion_recording_stop_time:
                recorder.stop_recording()
                log.info("Stopped motion recording (post-motion timeout)")
                mqtt.publish_recording_state(False)
    except Exception:
        log.exception("Error handling motion recording")


def _check_storage_for_recording():
    settings = config.current_settings()
    max_percent = settings.get("STORAGE_MAX_PERCENT", 90)
    action = settings.get("STORAGE_FULL_ACTION", "pause")
    try:
        from . import system
        storage = system.get_storage_info()
        used_percent = storage.get("used_percent", 0)
        if used_percent >= max_percent:
            if action == "pause":
                log.warning(f"Storage at {used_percent}%, pausing recording")
                return False
            elif action == "overwrite":
                _delete_oldest_recording()
                return True
        return True
    except Exception:
        log.exception("Error checking storage")
        return True


def _delete_oldest_recording():
    try:
        from pathlib import Path
        recordings_root = Path(config.RECORDINGS_ROOT)
        if not recordings_root.exists():
            return
        files = list(recordings_root.rglob("*.mp4"))
        if not files:
            return
        oldest = min(files, key=lambda f: f.stat().st_mtime)
        oldest.unlink()
        log.info(f"Deleted oldest recording: {oldest}")
    except Exception:
        log.exception("Error deleting oldest recording")


def motion_detection_loop():
    global _motion_recording_stop_time
    prev_frame = None
    state.manual_display_override = False
    _apply_screen_control_mode()

    while True:
        try:
            lores_frame = picam2.capture_array("lores")
        except Exception:
            log.exception("Failed to capture lores frame")
            time.sleep(config.CHECK_INTERVAL)
            continue

        try:
            gray = lores_frame[:lores_frame.shape[0] // 3, :].copy()
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            if prev_frame is not None and time.time() > state.ignore_motion_until:
                delta = cv2.absdiff(prev_frame, gray)
                _, thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
                motion_score = cv2.countNonZero(thresh)
                is_motion = motion_score > config.MOTION_THRESHOLD

                if state.manual_display_override:
                    prev_frame = gray
                    time.sleep(60)
                    state.manual_display_override = False
                    continue

                _handle_motion_recording(is_motion)

                if is_motion:
                    state.last_motion_time = time.time()
                    _set_display_if_needed(True)
                    if not state.motion_event:
                        state.motion_event = True
                        mqtt.publish_motion(True)
                elif time.time() - state.last_motion_time > config.INACTIVITY_TIMEOUT:
                    _set_display_if_needed(False)
                    if state.motion_event:
                        state.motion_event = False
                        mqtt.publish_motion(False)

            prev_frame = gray
        except Exception:
            log.exception("Error during motion detection")
        time.sleep(config.CHECK_INTERVAL)


def _apply_screen_control_mode():
    mode = config.current_settings().get("SCREEN_CONTROL_MODE", "auto")
    if mode == "always_on":
        set_display(True)
        state.display_on = True
        mqtt.publish_display(True)
        log.info("Screen control mode: always_on")
    elif mode == "always_off":
        set_display(False)
        state.display_on = False
        mqtt.publish_display(False)
        log.info("Screen control mode: always_off")
    else:
        log.info("Screen control mode: auto (motion-based)")


def start_motion_thread():
    global _motion_thread
    with _motion_thread_lock:
        if _motion_thread is not None and _motion_thread.is_alive():
            return
        _motion_thread = threading.Thread(target=motion_detection_loop, daemon=True)
        _motion_thread.start()
        log.info("Motion detection thread started")


def apply_screen_mode():
    _apply_screen_control_mode()