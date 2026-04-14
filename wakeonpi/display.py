import logging
from . import config

log = logging.getLogger("Display")


def set_display(state):
    try:
        path = getattr(config, "BACKLIGHT_PATH", "/sys/class/backlight/10-0045/bl_power")
        with open(path, "w") as f:
            f.write("0" if state else "1")
    except Exception:
        log.exception("Failed to set backlight")