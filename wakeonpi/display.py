import logging
from . import config, state

log = logging.getLogger("Display")


def _get_backlight_path():
    return config.current_settings().get("BACKLIGHT_PATH") or "/sys/class/backlight/10-0045/bl_power"


def _get_brightness_path():
    return config.current_settings().get("BRIGHTNESS_PATH") or "/sys/class/backlight/10-0045/brightness"


def _get_brightness_max_path():
    return config.current_settings().get("BRIGHTNESS_MAX_PATH") or "/sys/class/backlight/10-0045/max_brightness"


def set_display(on):
    try:
        with open(_get_backlight_path(), "w") as f:
            f.write("0" if on else "1")
    except Exception:
        log.exception("Failed to set backlight")


def get_max_brightness():
    try:
        with open(_get_brightness_max_path(), "r") as f:
            return int(f.read().strip())
    except Exception:
        return 255


def get_brightness():
    try:
        with open(_get_brightness_path(), "r") as f:
            current = int(f.read().strip())
        return int((current / get_max_brightness()) * 100)
    except Exception:
        return state.brightness_level


def set_brightness(percent):
    try:
        percent = max(5, min(100, int(percent)))
        value = int((percent / 100) * get_max_brightness())
        with open(_get_brightness_path(), "w") as f:
            f.write(str(value))
        with state.brightness_lock:
            state.brightness_level = percent
        return True
    except Exception:
        log.error("Failed to set brightness")
        return False