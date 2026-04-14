import json
import threading
import logging
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

from . import config, state
from .display import set_display

log = logging.getLogger("MQTT")

_client = None
_connected = False
_last_version = None


def _on_connect(client, userdata, flags, rc):
    global _connected
    _connected = True
    log.info(f"MQTT connected with rc={rc}")
    prefix = config.MQTT_TOPIC_PREFIX
    client.subscribe(f"{prefix}/command/screen/set")
    client.subscribe(f"{prefix}/command/browser/url_set")
    client.subscribe(f"{prefix}/command/browser/refresh")
    client.subscribe(f"{prefix}/command/camera/refresh")
    client.subscribe(f"{prefix}/command/recording/toggle")
    client.subscribe(f"{prefix}/command/settings/update")

    try:
        cam = getattr(state, "stream_url", None)
        if cam:
            publish_camera_stream_url(cam)
        from . import browser
        bro = browser.get_current_url()
        if bro:
            publish_browser_url(bro)
        elif getattr(state, "browser_url", None):
            publish_browser_url(state.browser_url)
        try:
            from . import recorder
            publish_recording_state(recorder.is_recording())
        except Exception:
            pass
    except Exception:
        log.exception("Failed to publish stream URLs on connect")

    try:
        version = _get_version()
        publish_state("system/version", str(version))
        global _last_version
        _last_version = str(version)
    except Exception:
        log.exception("Failed to publish system info")

    try:
        _publish_ha_discovery(prefix)
    except Exception:
        log.exception("Failed to publish HA discovery")


def _get_version():
    try:
        pjpath = Path(__file__).parent.parent / "pyproject.toml"
        if pjpath.exists():
            with pjpath.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("version") and "=" in line:
                        _, val = line.split("=", 1)
                        return val.strip().strip('"').strip("'")
    except Exception:
        pass
    return getattr(config, "VERSION", "0.0.1")


def _on_disconnect(client, userdata, rc):
    global _connected
    _connected = False
    log.info(f"MQTT disconnected rc={rc}")


def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        log.debug(f"MQTT message: topic={msg.topic} payload={payload}")
        prefix = config.MQTT_TOPIC_PREFIX

        if msg.topic == f"{prefix}/command/screen/set":
            val = payload.lower() in ("1", "true", "on", "open")
            state.manual_display_override = True
            set_display(val)
            state.display_on = val
            publish_display(val)

        elif msg.topic == f"{prefix}/command/browser/url_set":
            try:
                from . import browser
                browser.show_url(payload, force=True, one_shot=True)
                publish_browser_url(payload)
            except Exception:
                log.exception("Failed to set browser URL")

        elif msg.topic == f"{prefix}/command/browser/refresh":
            try:
                from . import browser
                browser.refresh()
            except Exception:
                log.exception("Failed to refresh browser")

        elif msg.topic == f"{prefix}/command/camera/refresh":
            cam = getattr(state, "stream_url", None)
            if cam:
                publish_camera_stream_url(cam)

        elif msg.topic == f"{prefix}/command/recording/toggle":
            try:
                from . import recorder
                if recorder.is_recording():
                    recorder.stop_recording()
                    publish_recording_state(False)
                else:
                    ok, _ = recorder.start_recording(config.RECORDINGS_ROOT)
                    if ok:
                        publish_recording_state(True)
            except Exception:
                log.exception("Failed to toggle recording")

        elif msg.topic == f"{prefix}/command/settings/update":
            try:
                data = json.loads(payload)
                allowed = set(config.current_settings().keys())
                updates = {k: v for k, v in data.items() if k in allowed}
                if updates:
                    config.update_settings(**updates)
                    restart()
                    try:
                        from . import browser
                        browser.stop()
                        browser.start()
                    except Exception:
                        log.exception("Failed to restart browser after settings update")
            except Exception:
                log.exception("Failed to parse settings update")
    except Exception:
        log.exception("Error in MQTT message handler")


def start():
    global _client, _connected
    if mqtt is None:
        log.warning("paho-mqtt not installed; MQTT disabled")
        _connected = False
        return
    if _client is not None and _connected:
        return
    if _client is not None:
        try:
            stop()
        except Exception:
            pass

    cfg = config.current_settings()
    _client = mqtt.Client()
    if cfg.get("MQTT_USERNAME"):
        _client.username_pw_set(cfg.get("MQTT_USERNAME"), cfg.get("MQTT_PASSWORD"))
    _client.on_connect = _on_connect
    _client.on_message = _on_message
    _client.on_disconnect = _on_disconnect
    try:
        host = cfg.get("MQTT_HOST") or "localhost"
        port = int(cfg.get("MQTT_PORT") or 1883)
        log.info(f"Connecting to MQTT {host}:{port}")
        _client.connect(host, port)
        threading.Thread(target=_client.loop_forever, daemon=True).start()
    except Exception:
        log.exception("MQTT connect error")
        _client = None
        _connected = False


def stop():
    global _client, _connected
    if _client is None:
        _connected = False
        return
    try:
        _client.disconnect()
    except Exception:
        pass
    _client = None
    _connected = False


def restart():
    stop()
    start()


def is_connected():
    return _client is not None and _connected


def publish(topic_suffix, payload):
    if _client is None:
        return
    try:
        full = f"{config.MQTT_TOPIC_PREFIX}/{topic_suffix}"
        _client.publish(full, payload, retain=True)
    except Exception:
        log.exception(f"Failed to publish: {topic_suffix}")


def publish_state(path, payload):
    global _last_version
    if path == "system/version":
        _last_version = payload
    publish(f"state/{path}", payload)


def publish_motion(is_motion):
    publish_state("motion", "ON" if is_motion else "OFF")


def publish_display(is_on):
    publish_state("screen", "ON" if is_on else "OFF")


def publish_camera_stream_url(url):
    publish_state("camera/stream_url", url)


def publish_browser_url(url):
    state.browser_url = url
    publish_state("browser/url", url)


def publish_recording_state(is_on):
    publish_state("recording/active", "ON" if is_on else "OFF")


def get_system_version():
    return _last_version


def _publish_ha_discovery(prefix):
    if _client is None:
        return

    device = {
        "identifiers": [prefix],
        "name": "WakeOnPi",
        "manufacturer": "VithuselServices",
        "model": "Raspberry Pi",
    }

    discoveries = [
        ("binary_sensor", f"{prefix}_motion", {
            "name": "Motion",
            "state_topic": f"{prefix}/state/motion",
            "payload_on": "ON",
            "payload_off": "OFF",
        }),
        ("switch", f"{prefix}_screen", {
            "name": "Screen",
            "command_topic": f"{prefix}/command/screen/set",
            "state_topic": f"{prefix}/state/screen",
            "payload_on": "ON",
            "payload_off": "OFF",
        }),
        ("sensor", f"{prefix}_version", {
            "name": "Version",
            "state_topic": f"{prefix}/state/system/version",
        }),
        ("text", f"{prefix}_browser_url", {
            "name": "Browser URL",
            "state_topic": f"{prefix}/state/browser/url",
            "command_topic": f"{prefix}/command/browser/url_set",
        }),
        ("button", f"{prefix}_browser_refresh", {
            "name": "Browser Refresh",
            "command_topic": f"{prefix}/command/browser/refresh",
        }),
        ("binary_sensor", f"{prefix}_recording_active", {
            "name": "Recording Active",
            "state_topic": f"{prefix}/state/recording/active",
        }),
        ("switch", f"{prefix}_recording", {
            "name": "Recording",
            "command_topic": f"{prefix}/command/recording/toggle",
            "state_topic": f"{prefix}/state/recording/active",
            "payload_on": "ON",
            "payload_off": "OFF",
        }),
        ("sensor", f"{prefix}_camera_url", {
            "name": "Camera URL",
            "state_topic": f"{prefix}/state/camera/stream_url",
        }),
    ]

    stream = getattr(state, "stream_url", None)
    if stream:
        discoveries.append(("camera", f"{prefix}_camera", {
            "name": "Stream",
            "mjpeg_url": stream,
        }))

    for component, unique_id, payload in discoveries:
        payload["unique_id"] = unique_id
        payload["device"] = device
        try:
            _client.publish(f"homeassistant/{component}/{unique_id}/config", json.dumps(payload), retain=True)
        except Exception:
            log.exception(f"Failed to publish HA {component} discovery")