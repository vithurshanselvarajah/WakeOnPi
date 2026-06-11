import logging
import secrets
import json
from pathlib import Path
from . import db

log = logging.getLogger("Config")
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
    "HTTP_PASSWORD_HASH": None,
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
    "STREAM_USERNAME": "stream",
    "STREAM_PASSWORD": None,
    "SECRET_KEY": None,
    "UPDATE_CHANNEL": "release",
    "SETUP_COMPLETE": False,
}


def _cast_value(key, value):
    if value is None or value == "None":
        return None
    if key not in DEFAULTS:
        return value
    default_val = DEFAULTS[key]
    if isinstance(default_val, bool):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(default_val, int):
        try:
            return int(value)
        except ValueError:
            return default_val
    if isinstance(default_val, float):
        try:
            return float(value)
        except ValueError:
            return default_val
    return value


def _load():
    legacy_data = {}
    if SETTINGS_FILE.exists():
        log.info("Legacy settings.json found. Migrating to SQLite database...")
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                legacy_data = json.load(f)
            old_password = legacy_data.get("HTTP_PASSWORD")
            if old_password and old_password != "password123":
                legacy_data["HTTP_PASSWORD_HASH"] = db.hash_password(old_password)
                legacy_data["SETUP_COMPLETE"] = True
            elif old_password == "password123":
                legacy_data["SETUP_COMPLETE"] = False
        except Exception:
            log.exception("Failed to parse legacy settings.json")

    data = {}
    db_settings = db.get_all_settings()

    for k, v in DEFAULTS.items():
        if k in db_settings:
            data[k] = _cast_value(k, db_settings[k])
        elif k in legacy_data:
            data[k] = legacy_data[k]
            db.set_setting(k, str(legacy_data[k]))
        else:
            data[k] = v
            db.set_setting(k, str(v))

    if not data.get("STREAM_PASSWORD"):
        data["STREAM_PASSWORD"] = secrets.token_urlsafe(16)
        db.set_setting("STREAM_PASSWORD", data["STREAM_PASSWORD"])
    if not data.get("SECRET_KEY"):
        data["SECRET_KEY"] = secrets.token_hex(32)
        db.set_setting("SECRET_KEY", data["SECRET_KEY"])

    if SETTINGS_FILE.exists():
        try:
            SETTINGS_FILE.unlink()
            log.info("Migration successful. Legacy settings.json removed.")
        except Exception:
            log.exception("Failed to delete legacy settings.json file")

    return data


def _save(data):
    for k, v in data.items():
        db.set_setting(k, str(v) if v is not None else None)


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
HTTP_PASSWORD_HASH = _settings.get("HTTP_PASSWORD_HASH")
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
STREAM_USERNAME = _settings.get("STREAM_USERNAME", "stream")
STREAM_PASSWORD = _settings.get("STREAM_PASSWORD")
SECRET_KEY = _settings.get("SECRET_KEY")
UPDATE_CHANNEL = _settings.get("UPDATE_CHANNEL", "release")
SETUP_COMPLETE = _settings.get("SETUP_COMPLETE", False)


def get_log_level():
    return logging.DEBUG if DEBUG_MODE else logging.INFO


def update_settings(**kwargs):
    global MOTION_THRESHOLD, INACTIVITY_TIMEOUT, CHECK_INTERVAL
    global MQTT_HOST, MQTT_PORT, MQTT_TOPIC_PREFIX, MQTT_USERNAME, MQTT_PASSWORD
    global HASS_DASHBOARD_URL, HTTP_USERNAME, HTTP_PASSWORD_HASH, BACKLIGHT_PATH, RECORDINGS_ROOT
    global BRIGHTNESS_PATH, BRIGHTNESS_MAX_PATH
    global STREAM_RESOLUTION, STREAM_FPS, STREAM_QUALITY
    global OVERLAY_ENABLED, OVERLAY_SHOW_TIME, OVERLAY_SHOW_STATS, OVERLAY_POSITION
    global SERVICE_PORT, DEBUG_MODE
    global STREAM_USERNAME, STREAM_PASSWORD, SECRET_KEY, UPDATE_CHANNEL, SETUP_COMPLETE

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
    HTTP_PASSWORD_HASH = _settings.get("HTTP_PASSWORD_HASH")
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
    STREAM_USERNAME = _settings.get("STREAM_USERNAME", "stream")
    STREAM_PASSWORD = _settings.get("STREAM_PASSWORD")
    SECRET_KEY = _settings.get("SECRET_KEY")
    UPDATE_CHANNEL = _settings.get("UPDATE_CHANNEL", "release")
    SETUP_COMPLETE = _settings.get("SETUP_COMPLETE", False)

    if "DEBUG_MODE" in kwargs:
        logging.getLogger().setLevel(get_log_level())

    return _settings.copy()


def current_settings():
    return _settings.copy()


def load_settings():
    global _settings
    global MOTION_THRESHOLD, INACTIVITY_TIMEOUT, CHECK_INTERVAL
    global MQTT_HOST, MQTT_PORT, MQTT_TOPIC_PREFIX, MQTT_USERNAME, MQTT_PASSWORD
    global HASS_DASHBOARD_URL, HTTP_USERNAME, HTTP_PASSWORD_HASH, BACKLIGHT_PATH, RECORDINGS_ROOT
    global BRIGHTNESS_PATH, BRIGHTNESS_MAX_PATH
    global STREAM_RESOLUTION, STREAM_FPS, STREAM_QUALITY
    global OVERLAY_ENABLED, OVERLAY_SHOW_TIME, OVERLAY_SHOW_STATS, OVERLAY_POSITION
    global SERVICE_PORT, DEBUG_MODE
    global STREAM_USERNAME, STREAM_PASSWORD, SECRET_KEY, UPDATE_CHANNEL, SETUP_COMPLETE

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
    HTTP_PASSWORD_HASH = _settings.get("HTTP_PASSWORD_HASH")
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
    STREAM_USERNAME = _settings.get("STREAM_USERNAME", "stream")
    STREAM_PASSWORD = _settings.get("STREAM_PASSWORD")
    SECRET_KEY = _settings.get("SECRET_KEY")
    UPDATE_CHANNEL = _settings.get("UPDATE_CHANNEL", "release")
    SETUP_COMPLETE = _settings.get("SETUP_COMPLETE", False)

