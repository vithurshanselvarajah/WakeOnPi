import logging
from . import config, state

log = logging.getLogger("Display")


def set_display(on):
    try:
        path = getattr(config, "BACKLIGHT_PATH", "/sys/class/backlight/10-0045/bl_power")
        with open(path, "w") as f:
            f.write("0" if on else "1")
    except Exception:
        log.exception("Failed to set backlight")


def get_max_brightness():
    try:
        path = getattr(config, "BRIGHTNESS_MAX_PATH", "/sys/class/backlight/10-0045/max_brightness")
        with open(path, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 255


def get_brightness():
    try:
        path = getattr(config, "BRIGHTNESS_PATH", "/sys/class/backlight/10-0045/brightness")
        with open(path, "r") as f:
            current = int(f.read().strip())
        max_val = get_max_brightness()
        return int((current / max_val) * 100)
    except Exception:
        return state.brightness_level


def set_brightness(percent):
    try:
        percent = max(5, min(100, int(percent)))
        max_val = get_max_brightness()
        value = int((percent / 100) * max_val)
        path = getattr(config, "BRIGHTNESS_PATH", "/sys/class/backlight/10-0045/brightness")
        with open(path, "w") as f:
            f.write(str(value))
        with state.brightness_lock:
            state.brightness_level = percent
        return True
    except Exception:
        log.error("Failed to set brightness")
        return False