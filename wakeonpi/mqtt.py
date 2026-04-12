import os
import json
import threading
import time
try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

from . import config, state
from .display import set_display

_client = None

def _on_connect(client, userdata, flags, rc):
    prefix = config.MQTT_TOPIC_PREFIX
    client.subscribe(f"{prefix}/screen/set")

def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        if msg.topic.endswith("/screen/set"):
            val = payload.lower() in ("1", "true", "on", "open")
            state.manual_display_override = True
            set_display(val)
            state.display_on = val
            publish_display(val)
    except Exception:
        pass

def start():
    global _client
    if mqtt is None:
        print("paho-mqtt not installed; MQTT disabled")
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
        _client.connect(cfg.get("MQTT_HOST") or "localhost", int(cfg.get("MQTT_PORT") or 1883))
        t = threading.Thread(target=_client.loop_forever, daemon=True)
        t.start()
    except Exception as e:
        print("MQTT connect error:", e)
        _client = None

def publish(topic_suffix, payload):
    if _client is None:
        return
    try:
        _client.publish(f"{config.MQTT_TOPIC_PREFIX}/{topic_suffix}", payload, retain=True)
    except Exception:
        pass

def publish_motion(is_motion):
    publish("motion", "ON" if is_motion else "OFF")

def publish_display(is_on):
    publish("screen", "ON" if is_on else "OFF")

def publish_stream_url(url):
    publish("stream_url", url)