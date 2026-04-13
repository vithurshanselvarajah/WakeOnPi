import json
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
    "HTTP_USERNAME": "admin",
    "HTTP_PASSWORD": "admin123",
}

MOTION_THRESHOLD = 1500
INACTIVITY_TIMEOUT = 15
CHECK_INTERVAL = 1.0
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

def update_settings(**kwargs):
    global MOTION_THRESHOLD, INACTIVITY_TIMEOUT, CHECK_INTERVAL
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
    return _settings.copy()

def current_settings():
    return _settings.copy()