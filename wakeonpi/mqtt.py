import os
import json
import threading
import time
import logging
try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

from . import config, state
from .display import set_display
from pathlib import Path

log = logging.getLogger("MQTT")

_client = None
_connected = False


def _on_connect(client, userdata, flags, rc):
    global _connected
    _connected = True
    log.info(f"MQTT connected with rc={rc}")
    prefix = config.MQTT_TOPIC_PREFIX
    client.subscribe(f"{prefix}/command/screen/set")
    client.subscribe(f"{prefix}/command/browser/url_set")
    client.subscribe(f"{prefix}/command/browser/refresh")
    client.subscribe(f"{prefix}/command/browser/pause")
    client.subscribe(f"{prefix}/command/browser/resume")
    client.subscribe(f"{prefix}/command/camera/refresh")
    client.subscribe(f"{prefix}/command/settings/update")

    try:
        cam = getattr(state, "stream_url", None)
        if cam:
            publish_camera_stream_url(cam)
        import wakeonpi.browser as browser
        bro = getattr(browser, "get_current_url", lambda: None)()
        if bro:
            publish_browser_current_page(bro)
    except Exception:
        log.exception("Failed to publish current stream URLs on MQTT connect")

    try:
        uptime = int(time.time() - getattr(state, "start_time", time.time()))
        try:
            pjpath = Path(__file__).parent.parent / 'pyproject.toml'
            version = None
            if pjpath.exists():
                with pjpath.open('r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('version') and '=' in line:
                            _, val = line.split('=', 1)
                            version = val.strip().strip('"').strip("'")
                            break
        except Exception:
            version = getattr(config, 'VERSION', '0.0.1')
        publish_state('system/uptime', str(uptime))
        publish_state('system/version', str(version))
    except Exception:
        log.exception("Failed to publish system info on MQTT connect")


def _on_disconnect(client, userdata, rc):
    global _connected
    _connected = False
    log.info(f"MQTT disconnected rc={rc}")


def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        log.debug(f"MQTT message received: topic={msg.topic} payload={payload}")
        prefix = config.MQTT_TOPIC_PREFIX
        if msg.topic == f"{prefix}/command/screen/set":
            val = payload.lower() in ("1", "true", "on", "open")
            state.manual_display_override = True
            set_display(val)
            state.display_on = val
            publish_display(val)
        elif msg.topic == f"{prefix}/command/browser/url_set":
            try:
                import wakeonpi.browser as browser
                browser.show_url(payload, force=True, one_shot=True)
                publish_browser_current_page(payload)
            except Exception:
                log.exception("MQTT handler failed to set browser URL")
        elif msg.topic == f"{prefix}/command/browser/refresh":
            try:
                import wakeonpi.browser as browser
                browser.refresh()
            except Exception:
                log.exception("MQTT handler failed to refresh browser")
        elif msg.topic == f"{prefix}/command/browser/pause":
            try:
                import wakeonpi.browser as browser
                browser.pause()
            except Exception:
                log.exception("MQTT handler failed to pause browser")
        elif msg.topic == f"{prefix}/command/browser/resume":
            try:
                import wakeonpi.browser as browser
                browser.resume()
            except Exception:
                log.exception("MQTT handler failed to resume browser")
        elif msg.topic == f"{prefix}/command/camera/refresh":
            try:
                cam = getattr(state, "stream_url", None)
                if cam:
                    publish_camera_stream_url(cam)
            except Exception:
                log.exception("MQTT handler failed to refresh camera stream URL")
        elif msg.topic == f"{prefix}/command/settings/update":
            try:
                data = json.loads(payload)
                allowed = set(config.current_settings().keys())
                updates = {k: v for k, v in data.items() if k in allowed}
                if updates:
                    config.update_settings(**updates)
                    try:
                        restart()
                    except Exception:
                        log.exception("Failed to restart MQTT after settings update via MQTT")
                    try:
                        import wakeonpi.browser as browser
                        browser.stop()
                        browser.start()
                    except Exception:
                        log.exception("Failed to restart browser after settings update via MQTT")
            except Exception:
                log.exception("Failed to parse settings update message")
    except Exception:
        log.exception("Unexpected error in MQTT on_message handler")


def start():
    global _client, _connected
    if mqtt is None:
        log.warning("paho-mqtt not installed; MQTT disabled")
        _connected = False
        return
    if _client is not None and _connected:
        return
    if _client is not None and not _connected:
        try:
            stop()
        except Exception:
            log.exception("Error stopping existing MQTT client")

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
        t = threading.Thread(target=_client.loop_forever, daemon=True)
        t.start()

    except Exception:
        log.exception("MQTT connect error")
        try:
            _client = None
        except Exception:
            pass
        _connected = False


def stop():
    global _client, _connected
    if _client is None:
        _connected = False
        return
    try:
        try:
            _client.disconnect()
        except Exception:
            pass
        _client = None
    finally:
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
        log.exception(f"Failed to publish MQTT message: {topic_suffix} -> {payload}")

def publish_state(path, payload):
    publish(f"state/{path}", payload)

def publish_motion(is_motion):
    publish_state("motion", "ON" if is_motion else "OFF")

def publish_display(is_on):
    publish_state("screen", "ON" if is_on else "OFF")

def publish_camera_stream_url(url):
    publish_state("camera/stream_url", url)

def publish_browser_current_page(url):
    publish_state("browser/current_page", url)
    
def publish_command(path, payload):
    publish(f"command/{path}", payload)