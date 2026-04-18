import socket
import logging
from pathlib import Path
import cv2
from flask import Flask, Response, stream_with_context, request, redirect, url_for, render_template

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from . import state, config, mqtt, browser, recorder
from .camera import picam2, switch_to_full_mode, switch_to_lores_mode_if_needed
from .auth import requires_auth
from .motion import start_motion_thread

app = Flask(__name__)
log = logging.getLogger("App")

mqtt.start()
try:
    log.info("Starting browser service")
    browser.start()
except Exception:
    log.exception("Failed to start browser service")

start_motion_thread()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


host = get_local_ip()
port = 5000
state.stream_url = f"http://{host}:{port}"
mqtt.publish_camera_stream_url(state.stream_url)

SENSITIVE_PLACEHOLDER = "__**password_not_changed**__"
SETTINGS_KEYS = [
    "MOTION_THRESHOLD", "INACTIVITY_TIMEOUT", "CHECK_INTERVAL",
    "MQTT_HOST", "MQTT_PORT", "MQTT_TOPIC_PREFIX", "MQTT_USERNAME", "MQTT_PASSWORD",
    "HTTP_USERNAME", "HTTP_PASSWORD", "HASS_DASHBOARD_URL", "BACKLIGHT_PATH", "RECORDINGS_ROOT"
]


def _parse_setting(key, val):
    if key == "MOTION_THRESHOLD":
        return int(val)
    if key in ("INACTIVITY_TIMEOUT", "CHECK_INTERVAL"):
        return float(val)
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


@app.route("/")
@requires_auth
def video_feed():
    @stream_with_context
    def gen():
        with state.clients_lock:
            state.clients_connected += 1
        switch_to_full_mode()
        try:
            while True:
                frame = picam2.capture_array("main")
                frame = cv2.resize(frame, (854, 480))
                ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ret:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        finally:
            with state.clients_lock:
                state.clients_connected -= 1
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
