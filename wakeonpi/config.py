import logging
import secrets
import json
from pathlib import Path
from . import db

log = logging.getLogger("Config")
TEMPLATE_FILE = Path(__file__).parent / "settings_template.json"


def _load_defaults():
    try:
        with TEMPLATE_FILE.open("r", encoding="utf-8") as f:
            defaults = json.load(f)
    except Exception:
        log.exception("Failed to load settings template settings_template.json")
        defaults = {}

    # Resolve relative paths (like RECORDINGS_ROOT)
    if "RECORDINGS_ROOT" in defaults and defaults["RECORDINGS_ROOT"]:
        p = Path(defaults["RECORDINGS_ROOT"])
        if not p.is_absolute():
            defaults["RECORDINGS_ROOT"] = str(Path(__file__).parent / p)

    return defaults


DEFAULTS = _load_defaults()


def _cast_value(key, value):
    if value is None or value == "None":
        return None
    if key not in DEFAULTS:
        return value
    default_val = DEFAULTS[key]
    if isinstance(default_val, bool):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")
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
    data = {}
    db_settings = db.get_all_settings()

    for k, v in DEFAULTS.items():
        if k in db_settings:
            data[k] = _cast_value(k, db_settings[k])
        else:
            data[k] = v
            db.set_setting(k, str(v) if v is not None else None)

    if not data.get("STREAM_PASSWORD"):
        data["STREAM_PASSWORD"] = secrets.token_urlsafe(16)
        db.set_setting("STREAM_PASSWORD", data["STREAM_PASSWORD"])
    if not data.get("SECRET_KEY"):
        data["SECRET_KEY"] = secrets.token_hex(32)
        db.set_setting("SECRET_KEY", data["SECRET_KEY"])

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
            _settings[k] = _cast_value(k, v)
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

