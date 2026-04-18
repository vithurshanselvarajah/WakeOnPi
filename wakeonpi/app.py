import socket
import json
import time
import threading
from pathlib import Path
import cv2
from flask import Flask, Response, stream_with_context, request, redirect, url_for, render_template, jsonify

from . import config
from .logging_config import setup_logging

setup_logging(config.DEBUG_MODE)

import logging
log = logging.getLogger("App")

from . import state, mqtt, browser, recorder, system, overlay
from .camera import picam2, switch_to_full_mode, switch_to_lores_mode_if_needed, get_stream_settings, reconfigure as reconfigure_camera
from .auth import requires_auth
from .motion import start_motion_thread
from .display import set_display, set_brightness, get_brightness

try:
    from flask_sock import Sock
    WEBSOCKET_ENABLED = True
except ImportError:
    WEBSOCKET_ENABLED = False
    log.warning("flask-sock not installed, WebSocket support disabled")

app = Flask(__name__)

if WEBSOCKET_ENABLED:
    sock = Sock(app)

log.info("Starting system stats service")
system.start()
log.info("Starting MQTT service")
mqtt.start()
try:
    log.info("Starting browser service")
    browser.start()
except Exception:
    log.error("Failed to start browser service")

start_motion_thread()
_stats_broadcast_thread = None


host = state.get_system_ip()
state.stream_url = f"http://{host}:{config.SERVICE_PORT}/stream"
mqtt.publish_system_ip(host)

SENSITIVE_PLACEHOLDER = "__**password_not_changed**__"
SETTINGS_KEYS = [
    "MOTION_THRESHOLD", "INACTIVITY_TIMEOUT", "CHECK_INTERVAL",
    "MQTT_HOST", "MQTT_PORT", "MQTT_TOPIC_PREFIX", "MQTT_USERNAME", "MQTT_PASSWORD",
    "HTTP_USERNAME", "HTTP_PASSWORD", "HASS_DASHBOARD_URL", "BACKLIGHT_PATH", "RECORDINGS_ROOT",
    "BRIGHTNESS_PATH", "BRIGHTNESS_MAX_PATH", "STREAM_RESOLUTION", "STREAM_FPS", "STREAM_QUALITY",
    "OVERLAY_ENABLED", "OVERLAY_SHOW_TIME", "OVERLAY_SHOW_STATS", "OVERLAY_POSITION",
    "SERVICE_PORT", "DEBUG_MODE"
]


def _parse_setting(key, val):
    if key == "MOTION_THRESHOLD":
        return int(val)
    if key in ("INACTIVITY_TIMEOUT", "CHECK_INTERVAL"):
        return float(val)
    if key in ("STREAM_FPS", "STREAM_QUALITY", "SERVICE_PORT"):
        return int(val)
    if key in ("OVERLAY_ENABLED", "OVERLAY_SHOW_TIME", "OVERLAY_SHOW_STATS", "DEBUG_MODE"):
        return val.lower() in ("true", "1", "on", "yes") if isinstance(val, str) else bool(val)
    if key in ("MQTT_PASSWORD", "HTTP_PASSWORD"):
        return val if val != SENSITIVE_PLACEHOLDER else None
    return val


def _test_path_writable(path):
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        testfile = p / '.writetest'
        testfile.write_text('ok')
        testfile.unlink(missing_ok=True)
        return True
    except Exception:
        return False


@app.route("/settings", methods=["GET", "POST"])
@requires_auth
def settings():
    if request.method == "POST":
        updates = {}
        for key in SETTINGS_KEYS:
            if key not in request.form:
                continue
            val = request.form.get(key)
            if key in ("MQTT_PASSWORD", "HTTP_PASSWORD") and val == SENSITIVE_PLACEHOLDER:
                continue
            try:
                updates[key] = _parse_setting(key, val) if val else (None if key.endswith("PASSWORD") else val)
            except Exception:
                continue

        if updates:
            config.update_settings(**updates)
            try:
                mqtt.restart()
            except Exception:
                log.exception("Failed to restart MQTT after settings change")

            if "RECORDINGS_ROOT" in updates:
                rr = updates["RECORDINGS_ROOT"] or config.RECORDINGS_ROOT
                state.temp_recordings_test = {"path": rr, "writable": _test_path_writable(rr)}

            if "BACKLIGHT_PATH" in updates and updates["BACKLIGHT_PATH"]:
                bp = updates["BACKLIGHT_PATH"]
                try:
                    with open(bp, 'w') as f:
                        f.write('0')
                    state.temp_backlight_test = {"path": bp, "writable": True}
                except Exception:
                    state.temp_backlight_test = {"path": bp, "writable": False}

        return redirect(url_for("settings"))

    s = config.current_settings()
    pwd_display = SENSITIVE_PLACEHOLDER if s.get("MQTT_PASSWORD") else ""
    http_pwd_display = SENSITIVE_PLACEHOLDER if s.get("HTTP_PASSWORD") else ""

    status = {
        "mqtt_connected": mqtt.is_connected(),
        "mqtt_host": s.get("MQTT_HOST"),
        "mqtt_port": s.get("MQTT_PORT"),
        "mqtt_topic_prefix": config.MQTT_TOPIC_PREFIX,
        "motion_event": state.motion_event,
        "display_on": state.display_on,
        "clients_connected": state.clients_connected,
        "stream_url": getattr(state, "stream_url", None),
        "version": mqtt.get_system_version() or "N/A",
        "recording_active": recorder.is_recording(),
        "recording_file": recorder.get_current_file(),
    }

    try:
        ctrl = browser._get_controller()
        proc = getattr(ctrl, "_proc", None)
        status["browser_running"] = proc is not None and proc.poll() is None
        status["browser_current_url"] = ctrl.current_url or browser.get_current_url() or s.get("HASS_DASHBOARD_URL")
    except Exception:
        status["browser_running"] = False
        status["browser_current_url"] = None

    bl_test = getattr(state, "temp_backlight_test", None)
    status["last_backlight_test"] = bl_test
    status["backlight_path"] = bl_test["path"] if bl_test else s.get("BACKLIGHT_PATH")
    status["backlight_writable"] = bl_test["writable"] if bl_test else None

    rec_test = getattr(state, "temp_recordings_test", None)
    status["last_recordings_test"] = rec_test
    status["recordings_root"] = rec_test["path"] if rec_test else s.get("RECORDINGS_ROOT")
    status["recordings_writable"] = rec_test["writable"] if rec_test else None

    return render_template("settings.html", s=s, pwd_display=pwd_display, http_pwd_display=http_pwd_display, status=status)


@app.route("/settings/mqtt/reconnect", methods=["POST"])
@requires_auth
def settings_mqtt_reconnect():
    try:
        mqtt.restart()
        return "", 204
    except Exception:
        log.exception("Failed to reconnect MQTT")
        return "Error", 500


@app.route("/settings/browser/refresh", methods=["POST"])
@requires_auth
def settings_browser_refresh():
    try:
        browser.refresh()
        return "", 204
    except Exception:
        log.exception("Failed to refresh browser")
        return "Error", 500


@app.route("/settings/restart", methods=["POST"])
@requires_auth
def settings_restart():
    try:
        mqtt.restart()
        browser.stop()
        browser.start()
        return "", 204
    except Exception:
        log.exception("Failed to restart services")
        return "Error", 500


@app.route("/stream")
@requires_auth
def video_feed():
    @stream_with_context
    def gen():
        with state.clients_lock:
            state.clients_connected += 1
            mqtt.publish_clients_connected(state.clients_connected)
        switch_to_full_mode()
        try:
            stream_settings = get_stream_settings()
            res = stream_settings["resolution"]
            quality = stream_settings["quality"]
            while True:
                frame = picam2.capture_array("main")
                frame = cv2.resize(frame, res)
                frame = overlay.draw_overlay(frame)
                ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if ret:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        finally:
            with state.clients_lock:
                state.clients_connected -= 1
                mqtt.publish_clients_connected(state.clients_connected)
                if state.clients_connected == 0:
                    switch_to_lores_mode_if_needed()

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/motion_alerts")
def motion_alerts():
    return ("motion" if state.motion_event else "nomotion"), 200


@app.route("/settings/recording/toggle", methods=["POST"])
@requires_auth
def settings_recording_toggle():
    try:
        if recorder.is_recording():
            ok, res = recorder.stop_recording()
        else:
            ok, res = recorder.start_recording(config.RECORDINGS_ROOT)
        return ("", 204) if ok else (res, 500)
    except Exception:
        log.exception("Failed to toggle recording")
        return "Error", 500


@app.route("/settings/recording/status")
@requires_auth
def settings_recording_status():
    try:
        return {"active": recorder.is_recording(), "file": recorder.get_current_file()}, 200
    except Exception:
        log.exception("Failed to get recording status")
        return {"active": False, "file": None}, 500


@app.route("/health")
def health():
    return jsonify(system.get_health())


@app.route("/snapshot")
@requires_auth
def snapshot():
    try:
        switch_to_full_mode()
        time.sleep(0.1)
        frame = picam2.capture_array("main")
        stream_settings = get_stream_settings()
        frame = cv2.resize(frame, stream_settings["resolution"])
        frame = overlay.draw_overlay(frame)
        ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), stream_settings["quality"]])
        if ret:
            return Response(jpeg.tobytes(), mimetype="image/jpeg")
        return "Failed to capture", 500
    except Exception:
        log.exception("Failed to capture snapshot")
        return "Error", 500


@app.route("/api/status")
@requires_auth
def api_status():
    s = config.current_settings()
    stats = system.get_stats()
    storage = system.get_storage_info()
    try:
        ctrl = browser._get_controller()
        proc = getattr(ctrl, "_proc", None)
        browser_running = proc is not None and proc.poll() is None
        browser_url = ctrl.current_url or browser.get_current_url() or s.get("HASS_DASHBOARD_URL")
    except Exception:
        browser_running = False
        browser_url = None

    return jsonify({
        "mqtt_connected": mqtt.is_connected(),
        "motion_event": state.motion_event,
        "display_on": state.display_on,
        "brightness": get_brightness(),
        "clients_connected": state.clients_connected,
        "stream_url": state.stream_url,
        "version": mqtt.get_system_version() or "N/A",
        "recording_active": recorder.is_recording(),
        "recording_file": recorder.get_current_file(),
        "browser_running": browser_running,
        "browser_url": browser_url,
        "system": stats,
        "storage": storage,
    })


@app.route("/api/logs")
@requires_auth
def api_logs():
    level = request.args.get("level", "").upper()
    limit = int(request.args.get("limit", 100))
    logs = state.get_logs(level, limit)
    return jsonify(logs)


@app.route("/api/settings", methods=["GET", "POST"])
@requires_auth
def api_settings():
    if request.method == "GET":
        s = config.current_settings()
        if s.get("MQTT_PASSWORD"):
            s["MQTT_PASSWORD"] = SENSITIVE_PLACEHOLDER
        if s.get("HTTP_PASSWORD"):
            s["HTTP_PASSWORD"] = SENSITIVE_PLACEHOLDER
        return jsonify(s)

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    updates = {}
    for key, val in data.items():
        if key not in SETTINGS_KEYS:
            continue
        if key in ("MQTT_PASSWORD", "HTTP_PASSWORD") and val == SENSITIVE_PLACEHOLDER:
            continue
        try:
            updates[key] = _parse_setting(key, val) if val else (None if key.endswith("PASSWORD") else val)
        except Exception:
            continue

    if updates:
        config.update_settings(**updates)
        if any(k.startswith("STREAM_") for k in updates):
            reconfigure_camera()
        mqtt.restart()
        broadcast_status()

    return jsonify({"success": True})


@app.route("/api/display", methods=["POST"])
@requires_auth
def api_display():
    data = request.get_json()
    if data.get("on") is not None:
        val = data["on"]
        state.manual_display_override = True
        set_display(val)
        state.display_on = val
        mqtt.publish_display(val)
    if data.get("brightness") is not None:
        set_brightness(data["brightness"])
        mqtt.publish_brightness(data["brightness"])
    broadcast_status()
    return jsonify({"success": True})


@app.route("/api/overlay/notify", methods=["POST"])
@requires_auth
def api_overlay_notify():
    data = request.get_json()
    message = data.get("message", "")
    duration = data.get("duration", 5)
    overlay.set_notification(message, duration)
    return jsonify({"success": True})


def get_full_status():
    s = config.current_settings()
    stats = system.get_stats()
    storage = system.get_storage_info()
    try:
        ctrl = browser._get_controller()
        proc = getattr(ctrl, "_proc", None)
        browser_running = proc is not None and proc.poll() is None
        browser_url = ctrl.current_url or browser.get_current_url() or s.get("HASS_DASHBOARD_URL")
    except Exception:
        browser_running = False
        browser_url = None

    settings_safe = s.copy()
    if settings_safe.get("MQTT_PASSWORD"):
        settings_safe["MQTT_PASSWORD"] = SENSITIVE_PLACEHOLDER
    if settings_safe.get("HTTP_PASSWORD"):
        settings_safe["HTTP_PASSWORD"] = SENSITIVE_PLACEHOLDER

    return {
        "type": "status",
        "mqtt_connected": mqtt.is_connected(),
        "motion_event": state.motion_event,
        "display_on": state.display_on,
        "brightness": get_brightness(),
        "clients_connected": state.clients_connected,
        "stream_url": state.stream_url,
        "version": mqtt.get_system_version() or "N/A",
        "recording_active": recorder.is_recording(),
        "recording_file": recorder.get_current_file(),
        "browser_running": browser_running,
        "browser_url": browser_url,
        "system": stats,
        "storage": storage,
        "settings": settings_safe,
    }


def broadcast_status():
    if not WEBSOCKET_ENABLED:
        return
    status = get_full_status()
    with state.ws_clients_lock:
        dead = set()
        for ws in state.ws_clients:
            try:
                ws.send(json.dumps(status))
            except Exception:
                dead.add(ws)
        state.ws_clients -= dead


def _stats_broadcast_loop():
    while True:
        time.sleep(5)
        try:
            stats = system.get_stats()
            mqtt.publish_system_stats(stats)
            mqtt.publish_storage(stats["storage_free_gb"], stats["storage_total_gb"], stats["storage_percent"])
            broadcast_status()
        except Exception:
            pass


def start_stats_broadcast():
    global _stats_broadcast_thread
    if _stats_broadcast_thread and _stats_broadcast_thread.is_alive():
        return
    _stats_broadcast_thread = threading.Thread(target=_stats_broadcast_loop, daemon=True)
    _stats_broadcast_thread.start()


start_stats_broadcast()


if WEBSOCKET_ENABLED:
    @sock.route("/ws")
    def websocket(ws):
        with state.ws_clients_lock:
            state.ws_clients.add(ws)
        try:
            ws.send(json.dumps(get_full_status()))
            while True:
                message = ws.receive(timeout=30)
                if message is None:
                    continue
                try:
                    data = json.loads(message)
                    action = data.get("action")
                    if action == "get_status":
                        ws.send(json.dumps(get_full_status()))
                    elif action == "set_display":
                        val = data.get("on", True)
                        state.manual_display_override = True
                        set_display(val)
                        state.display_on = val
                        mqtt.publish_display(val)
                        broadcast_status()
                    elif action == "set_brightness":
                        val = data.get("value", 100)
                        set_brightness(val)
                        mqtt.publish_brightness(val)
                        broadcast_status()
                    elif action == "mqtt_reconnect":
                        mqtt.restart()
                        broadcast_status()
                    elif action == "browser_refresh":
                        browser.refresh()
                        broadcast_status()
                    elif action == "toggle_recording":
                        if recorder.is_recording():
                            recorder.stop_recording()
                        else:
                            recorder.start_recording(config.RECORDINGS_ROOT)
                        broadcast_status()
                    elif action == "restart_services":
                        mqtt.restart()
                        browser.stop()
                        browser.start()
                        broadcast_status()
                    elif action == "update_settings":
                        updates = {}
                        for key, val in data.get("settings", {}).items():
                            if key not in SETTINGS_KEYS:
                                continue
                            if key in ("MQTT_PASSWORD", "HTTP_PASSWORD") and val == SENSITIVE_PLACEHOLDER:
                                continue
                            try:
                                updates[key] = _parse_setting(key, val) if val else (None if key.endswith("PASSWORD") else val)
                            except Exception:
                                continue
                        if updates:
                            config.update_settings(**updates)
                            if any(k.startswith("STREAM_") for k in updates):
                                reconfigure_camera()
                            mqtt.restart()
                        broadcast_status()
                    elif action == "notify":
                        overlay.set_notification(data.get("message", ""), data.get("duration", 5))
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            with state.ws_clients_lock:
                state.ws_clients.discard(ws)
