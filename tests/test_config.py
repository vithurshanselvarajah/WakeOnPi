import importlib
import json
from pathlib import Path

import wakeonpi.config as config


def test_save_and_load_with_temp_file(tmp_path, monkeypatch):
    temp_file = tmp_path / "settings.json"
    monkeypatch.setattr(config, "SETTINGS_FILE", temp_file)

    data = {
        "MOTION_THRESHOLD": 42,
        "INACTIVITY_TIMEOUT": 3,
        "CHECK_INTERVAL": 0.5,
        "MQTT_HOST": "example",
        "MQTT_PORT": 1234,
        "MQTT_TOPIC_PREFIX": "testprefix",
        "MQTT_USERNAME": "u",
        "MQTT_PASSWORD": "p",
    }

    config._save(data)
    loaded = config._load()
    assert loaded["MOTION_THRESHOLD"] == 42
    assert loaded["MQTT_HOST"] == "example"


def test_update_settings_writes_and_updates(monkeypatch, tmp_path):
    importlib.reload(config)
    temp_file = tmp_path / "settings2.json"
    monkeypatch.setattr(config, "SETTINGS_FILE", temp_file)

    base = config.current_settings()
    new = config.update_settings(MOTION_THRESHOLD=999)
    assert new["MOTION_THRESHOLD"] == 999
    assert config.MOTION_THRESHOLD == 999
    assert temp_file.exists()
    content = json.loads(temp_file.read_text(encoding="utf-8"))
    assert content["MOTION_THRESHOLD"] == 999
