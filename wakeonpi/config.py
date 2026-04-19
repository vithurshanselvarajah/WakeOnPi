import json
import logging
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULTS = {
    "MOTION_THRESHOLD": 1500,
    "INACTIVITY_TIMEOUT": 60,
    "CHECK_INTERVAL": 1.0,
    "MQTT_HOST": "localhost",
    "MQTT_PORT": 1883,
    "MQTT_TOPIC_PREFIX": "wakeonpi",
    "MQTT_USERNAME": None,
    "MQTT_PASSWORD": None,
    "HASS_DASHBOARD_URL": "https://github.com/vithurshanselvarajah/WakeOnPi",
    "HTTP_USERNAME": "wakeonpi",
    "HTTP_PASSWORD": "password123",
    "BACKLIGHT_PATH": "/sys/class/backlight/10-0045/bl_power",
    "BRIGHTNESS_PATH": "/sys/class/backlight/10-0045/brightness",
    "BRIGHTNESS_MAX_PATH": "/sys/class/backlight/10-0045/max_brightness",
    "RECORDINGS_ROOT": str(Path(__file__).parent / "recordings"),
    "STREAM_RESOLUTION": "854x480",
    "STREAM_FPS": 10,
    "STREAM_QUALITY": 75,
    "OVERLAY_ENABLED": True,
    "OVERLAY_SHOW_TIME": True,
    "OVERLAY_SHOW_STATS": False,
    "OVERLAY_POSITION": "top-right",
    "SERVICE_PORT": 5000,
    "DEBUG_MODE": False,
    "CAMERA_ENABLED": True,
    "RECORDING_ENABLED": True,
    "RECORD_ON_MOTION": False,
    "RECORD_POST_MOTION_TIMEOUT": 10,
    "STORAGE_MAX_PERCENT": 90,
    "STORAGE_FULL_ACTION": "pause",
    "SCREEN_CONTROL_MODE": "auto",
    "BETA_UPDATES": False,
}


def _load():
    if not SETTINGS_FILE.exists():
        _save(DEFAULTS)
        return DEFAULTS.copy()
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = DEFAULTS.copy()
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    return data


def _save(data):
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


_settings = _load()

MOTION_THRESHOLD = _settings["MOTION_THRESHOLD"]
INACTIVITY_TIMEOUT = _settings["INACTIVITY_TIMEOUT"]
CHECK_INTERVAL = _settings["CHECK_INTERVAL"]
MQTT_HOST = _settings["MQTT_HOST"]
MQTT_PORT = _settings["MQTT_PORT"]
MQTT_TOPIC_PREFIX = _settings["MQTT_TOPIC_PREFIX"]
MQTT_USERNAME = _settings["MQTT_USERNAME"]
MQTT_PASSWORD = _settings["MQTT_PASSWORD"]
HASS_DASHBOARD_URL = _settings.get("HASS_DASHBOARD_URL")
HTTP_USERNAME = _settings.get("HTTP_USERNAME")
HTTP_PASSWORD = _settings.get("HTTP_PASSWORD")
BACKLIGHT_PATH = _settings.get("BACKLIGHT_PATH")
BRIGHTNESS_PATH = _settings.get("BRIGHTNESS_PATH")
BRIGHTNESS_MAX_PATH = _settings.get("BRIGHTNESS_MAX_PATH")
RECORDINGS_ROOT = _settings.get("RECORDINGS_ROOT")
STREAM_RESOLUTION = _settings.get("STREAM_RESOLUTION")
STREAM_FPS = _settings.get("STREAM_FPS")
STREAM_QUALITY = _settings.get("STREAM_QUALITY")
OVERLAY_ENABLED = _settings.get("OVERLAY_ENABLED")
OVERLAY_SHOW_TIME = _settings.get("OVERLAY_SHOW_TIME")
OVERLAY_SHOW_STATS = _settings.get("OVERLAY_SHOW_STATS")
OVERLAY_POSITION = _settings.get("OVERLAY_POSITION")
SERVICE_PORT = _settings.get("SERVICE_PORT", 5000)
DEBUG_MODE = _settings.get("DEBUG_MODE", False)


def get_log_level():
    return logging.DEBUG if DEBUG_MODE else logging.INFO


def update_settings(**kwargs):
    global MOTION_THRESHOLD, INACTIVITY_TIMEOUT, CHECK_INTERVAL
    global MQTT_HOST, MQTT_PORT, MQTT_TOPIC_PREFIX, MQTT_USERNAME, MQTT_PASSWORD
    global HASS_DASHBOARD_URL, HTTP_USERNAME, HTTP_PASSWORD, BACKLIGHT_PATH, RECORDINGS_ROOT
    global BRIGHTNESS_PATH, BRIGHTNESS_MAX_PATH
    global STREAM_RESOLUTION, STREAM_FPS, STREAM_QUALITY
    global OVERLAY_ENABLED, OVERLAY_SHOW_TIME, OVERLAY_SHOW_STATS, OVERLAY_POSITION
    global SERVICE_PORT, DEBUG_MODE

    for k, v in kwargs.items():
        if k in _settings:
            _settings[k] = v
    _save(_settings)

    MOTION_THRESHOLD = _settings["MOTION_THRESHOLD"]
    INACTIVITY_TIMEOUT = _settings["INACTIVITY_TIMEOUT"]
    CHECK_INTERVAL = _settings["CHECK_INTERVAL"]
    MQTT_HOST = _settings["MQTT_HOST"]
    MQTT_PORT = _settings["MQTT_PORT"]
    MQTT_TOPIC_PREFIX = _settings["MQTT_TOPIC_PREFIX"]
    MQTT_USERNAME = _settings["MQTT_USERNAME"]
    MQTT_PASSWORD = _settings["MQTT_PASSWORD"]
    HASS_DASHBOARD_URL = _settings.get("HASS_DASHBOARD_URL")
    HTTP_USERNAME = _settings.get("HTTP_USERNAME")
    HTTP_PASSWORD = _settings.get("HTTP_PASSWORD")
    BACKLIGHT_PATH = _settings.get("BACKLIGHT_PATH")
    BRIGHTNESS_PATH = _settings.get("BRIGHTNESS_PATH")
    BRIGHTNESS_MAX_PATH = _settings.get("BRIGHTNESS_MAX_PATH")
    RECORDINGS_ROOT = _settings.get("RECORDINGS_ROOT")
    STREAM_RESOLUTION = _settings.get("STREAM_RESOLUTION")
    STREAM_FPS = _settings.get("STREAM_FPS")
    STREAM_QUALITY = _settings.get("STREAM_QUALITY")
    OVERLAY_ENABLED = _settings.get("OVERLAY_ENABLED")
    OVERLAY_SHOW_TIME = _settings.get("OVERLAY_SHOW_TIME")
    OVERLAY_SHOW_STATS = _settings.get("OVERLAY_SHOW_STATS")
    OVERLAY_POSITION = _settings.get("OVERLAY_POSITION")
    SERVICE_PORT = _settings.get("SERVICE_PORT", 5000)
    DEBUG_MODE = _settings.get("DEBUG_MODE", False)

    if "DEBUG_MODE" in kwargs:
        logging.getLogger().setLevel(get_log_level())

    return _settings.copy()


def current_settings():
    return _settings.copy()
