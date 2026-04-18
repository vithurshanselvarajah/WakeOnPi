import json
import threading
import logging
import time
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

from . import config, state
from .display import set_display, set_brightness, get_brightness

log = logging.getLogger("MQTT")

_client = None
_connected = False
_last_version = None
_reconnect_thread = None
_stop_reconnect = threading.Event()
_reconnect_delay = 5
_max_reconnect_delay = 300


def _on_connect(client, userdata, flags, rc):
    global _connected, _reconnect_delay
    _connected = True
    _reconnect_delay = 5
    log.info(f"MQTT connected with rc={rc}")
    prefix = config.MQTT_TOPIC_PREFIX
    client.subscribe(f"{prefix}/command/screen/set")
    client.subscribe(f"{prefix}/command/screen/brightness")
    client.subscribe(f"{prefix}/command/browser/url_set")
    client.subscribe(f"{prefix}/command/browser/refresh")
    client.subscribe(f"{prefix}/command/recording/toggle")
    client.subscribe(f"{prefix}/command/settings/update")
    client.subscribe(f"{prefix}/command/display/notify")
    client.subscribe(f"{prefix}/command/display/notify/clear")

    try:
        ip = state.get_system_ip()
        publish_system_ip(ip)
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
    if rc != 0:
        _start_reconnect_thread()


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

        elif msg.topic == f"{prefix}/command/screen/brightness":
            try:
                val = int(payload)
                set_brightness(val)
                publish_brightness(val)
            except Exception:
                log.exception("Failed to set brightness")

        elif msg.topic == f"{prefix}/command/display/notify":
            try:
                from . import overlay
                data = json.loads(payload) if payload.startswith("{") else {"message": payload}
                message = data.get("message", payload)
                overlay.set_notification(message)
                publish_notification(message)
            except Exception:
                log.exception("Failed to set display notification")

        elif msg.topic == f"{prefix}/command/display/notify/clear":
            try:
                from . import overlay
                overlay.clear_notification()
                publish_notification("")
            except Exception:
                log.exception("Failed to clear display notification")

    except Exception:
        log.exception("Error in MQTT message handler")


def _reconnect_loop():
    global _reconnect_delay
    while not _stop_reconnect.is_set():
        if _connected:
            break
        log.info(f"Attempting MQTT reconnect in {_reconnect_delay}s...")
        _stop_reconnect.wait(_reconnect_delay)
        if _stop_reconnect.is_set():
            break
        try:
            if _client and not _connected:
                cfg = config.current_settings()
                host = cfg.get("MQTT_HOST") or "localhost"
                port = int(cfg.get("MQTT_PORT") or 1883)
                _client.reconnect()
                _reconnect_delay = 5
        except Exception:
            log.exception("MQTT reconnect failed")
            _reconnect_delay = min(_reconnect_delay * 2, _max_reconnect_delay)


def _start_reconnect_thread():
    global _reconnect_thread
    if _reconnect_thread and _reconnect_thread.is_alive():
        return
    _stop_reconnect.clear()
    _reconnect_thread = threading.Thread(target=_reconnect_loop, daemon=True)
    _reconnect_thread.start()


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
    host = cfg.get("MQTT_HOST")
    if not host:
        log.info("MQTT host not configured; skipping connection")
        _connected = False
        return

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
    _stop_reconnect.set()
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


def publish_system_ip(ip):
    publish_state("system/ip", ip)


def publish_browser_url(url):
    state.browser_url = url
    publish_state("browser/url", url)


def publish_recording_state(is_on):
    publish_state("recording/active", "ON" if is_on else "OFF")


def publish_brightness(level):
    publish_state("screen/brightness", str(level))


def publish_notification(message):
    publish_state("display/notification", message or "")


def publish_storage(free_gb, total_gb, percent):
    publish_state("storage/free_gb", str(free_gb))
    publish_state("storage/total_gb", str(total_gb))
    publish_state("storage/used_percent", str(percent))


def publish_system_stats(stats):
    publish_state("system/cpu_temp", str(stats.get("cpu_temp", 0)))
    publish_state("system/cpu_usage", str(stats.get("cpu_usage", 0)))
    publish_state("system/memory_percent", str(stats.get("memory_percent", 0)))
    publish_state("system/uptime", str(stats.get("uptime", 0)))


def get_system_version():
    return _last_version


def _publish_ha_discovery(prefix):
    if _client is None:
        return

    version = _get_version()
    settings_url = f"http://{state.get_system_ip()}:{config.SERVICE_PORT}/settings"
    device = {
        "identifiers": [prefix],
        "name": "WakeOnPi",
        "manufacturer": "WakeOnPi",
        "model": "Raspberry Pi 5",
        "sw_version": str(version),
        "configuration_url": settings_url,
    }

    discoveries = [
        ("binary_sensor", f"{prefix}_motion", {
            "name": "Motion",
            "device_class": "motion",
            "state_topic": f"{prefix}/state/motion",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:motion-sensor",
        }),
        ("switch", f"{prefix}_screen", {
            "name": "Screen",
            "device_class": "switch",
            "command_topic": f"{prefix}/command/screen/set",
            "state_topic": f"{prefix}/state/screen",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:monitor",
        }),
        ("number", f"{prefix}_brightness", {
            "name": "Brightness",
            "command_topic": f"{prefix}/command/screen/brightness",
            "state_topic": f"{prefix}/state/screen/brightness",
            "min": 5,
            "max": 100,
            "step": 5,
            "unit_of_measurement": "%",
            "icon": "mdi:brightness-6",
        }),
        ("sensor", f"{prefix}_version", {
            "name": "Version",
            "state_topic": f"{prefix}/state/system/version",
            "icon": "mdi:information-outline",
        }),
        ("text", f"{prefix}_browser_url", {
            "name": "Browser URL",
            "state_topic": f"{prefix}/state/browser/url",
            "command_topic": f"{prefix}/command/browser/url_set",
            "icon": "mdi:web",
        }),
        ("button", f"{prefix}_browser_refresh", {
            "name": "Browser Refresh",
            "command_topic": f"{prefix}/command/browser/refresh",
            "icon": "mdi:refresh",
        }),
        ("switch", f"{prefix}_recording", {
            "name": "Recording",
            "command_topic": f"{prefix}/command/recording/toggle",
            "state_topic": f"{prefix}/state/recording/active",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:record-rec",
        }),
        ("sensor", f"{prefix}_system_ip", {
            "name": "System IP",
            "state_topic": f"{prefix}/state/system/ip",
            "icon": "mdi:ip-network",
        }),
        ("sensor", f"{prefix}_cpu_temp", {
            "name": "CPU Temperature",
            "device_class": "temperature",
            "state_topic": f"{prefix}/state/system/cpu_temp",
            "unit_of_measurement": "°C",
            "icon": "mdi:thermometer",
        }),
        ("sensor", f"{prefix}_cpu_usage", {
            "name": "CPU Usage",
            "state_topic": f"{prefix}/state/system/cpu_usage",
            "unit_of_measurement": "%",
            "icon": "mdi:cpu-64-bit",
        }),
        ("sensor", f"{prefix}_memory", {
            "name": "Memory Usage",
            "state_topic": f"{prefix}/state/system/memory_percent",
            "unit_of_measurement": "%",
            "icon": "mdi:memory",
        }),
        ("sensor", f"{prefix}_uptime", {
            "name": "Uptime",
            "device_class": "duration",
            "state_topic": f"{prefix}/state/system/uptime",
            "unit_of_measurement": "s",
            "icon": "mdi:timer-outline",
        }),
        ("sensor", f"{prefix}_storage_free", {
            "name": "Storage Free",
            "device_class": "data_size",
            "state_topic": f"{prefix}/state/storage/free_gb",
            "unit_of_measurement": "GB",
            "icon": "mdi:harddisk",
        }),
        ("sensor", f"{prefix}_storage_used", {
            "name": "Storage Used",
            "state_topic": f"{prefix}/state/storage/used_percent",
            "unit_of_measurement": "%",
            "icon": "mdi:chart-pie",
        }),
        ("text", f"{prefix}_display_notify", {
            "name": "Display Notification",
            "command_topic": f"{prefix}/command/display/notify",
            "state_topic": f"{prefix}/state/display/notification",
            "icon": "mdi:message-alert",
        }),
        ("button", f"{prefix}_clear_notify", {
            "name": "Clear Notification",
            "command_topic": f"{prefix}/command/display/notify/clear",
            "icon": "mdi:message-off",
        }),
    ]

    for component, unique_id, payload in discoveries:
        payload["unique_id"] = unique_id
        payload["device"] = device
        payload["availability_topic"] = f"{prefix}/state/availability"
        try:
            _client.publish(f"homeassistant/{component}/{unique_id}/config", json.dumps(payload), retain=True)
        except Exception:
            log.exception(f"Failed to publish HA {component} discovery")

    _client.publish(f"{prefix}/state/availability", "online", retain=True)


def publish_clients_connected(count):
    publish_state("clients_connected", str(count))