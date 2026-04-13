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

log = logging.getLogger("MQTT")

_client = None

def _on_connect(client, userdata, flags, rc):
    log.info(f"MQTT connected with rc={rc}")
    prefix = config.MQTT_TOPIC_PREFIX
    client.subscribe(f"{prefix}/screen/set")
    client.subscribe(f"{prefix}/browser/url/set")
    client.subscribe(f"{prefix}/browser/refresh")
    client.subscribe(f"{prefix}/browser/pause")
    client.subscribe(f"{prefix}/browser/resume")

    try:
        import wakeonpi.browser as browser
        cur = getattr(browser, "get_current_url", lambda: None)()
        if not cur:
            cur = getattr(state, "stream_url", None)
        if cur:
            publish_stream_url(cur)
    except Exception:
        log.exception("Failed to publish current stream URL on MQTT connect")


def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        if msg.topic.endswith("/screen/set"):
            val = payload.lower() in ("1", "true", "on", "open")
            state.manual_display_override = True
            set_display(val)
            state.display_on = val
            publish_display(val)
        elif msg.topic.endswith("/browser/url/set"):
            try:
                import wakeonpi.browser as browser
                browser.show_url(payload, force=True, one_shot=True)
                publish_stream_url(payload)
            except Exception:
                log.exception("MQTT handler failed to set browser URL")
        elif msg.topic.endswith("/browser/refresh"):
            try:
                import wakeonpi.browser as browser
                browser.refresh()
            except Exception:
                log.exception("MQTT handler failed to refresh browser")
        elif msg.topic.endswith("/browser/pause"):
            try:
                import wakeonpi.browser as browser
                browser.pause()
            except Exception:
                log.exception("MQTT handler failed to pause browser")
        elif msg.topic.endswith("/browser/resume"):
            try:
                import wakeonpi.browser as browser
                browser.resume()
            except Exception:
                log.exception("MQTT handler failed to resume browser")
    except Exception:
        log.exception("Unexpected error in MQTT on_message handler")

def start():
    global _client
    if mqtt is None:
        log.warning("paho-mqtt not installed; MQTT disabled")
        return
    if _client is not None:
        return
    cfg = config.current_settings()
    _client = mqtt.Client()
    if cfg.get("MQTT_USERNAME"):
        _client.username_pw_set(cfg.get("MQTT_USERNAME"), cfg.get("MQTT_PASSWORD"))
    _client.on_connect = _on_connect
    _client.on_message = _on_message
    try:
        host = cfg.get("MQTT_HOST") or "localhost"
        port = int(cfg.get("MQTT_PORT") or 1883)
        log.info(f"Connecting to MQTT {host}:{port}")
        _client.connect(host, port)
        t = threading.Thread(target=_client.loop_forever, daemon=True)
        t.start()

        try:
            import wakeonpi.browser as browser
            cur = getattr(browser, "get_current_url", lambda: None)()
            if cur:
                publish_stream_url(cur)
        except Exception:
            log.exception("Failed to publish current browser URL on MQTT start")

    except Exception:
        log.exception("MQTT connect error")


def publish(topic_suffix, payload):
    if _client is None:
        return
    try:
        full = f"{config.MQTT_TOPIC_PREFIX}/{topic_suffix}"
        _client.publish(full, payload, retain=True)
    except Exception:
        log.exception(f"Failed to publish MQTT message: {topic_suffix} -> {payload}")

def publish_motion(is_motion):
    publish("motion", "ON" if is_motion else "OFF")

def publish_display(is_on):
    publish("screen", "ON" if is_on else "OFF")

def publish_stream_url(url):
    publish("stream_url", url)