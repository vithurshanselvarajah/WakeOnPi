import cv2
import socket
from flask import Flask, Response, stream_with_context, request, redirect, url_for, render_template
import logging

from . import state
from .camera import picam2, switch_to_full_mode, switch_to_lores_mode_if_needed
from .auth import requires_auth
from . import motion, mqtt, config, browser

app = Flask(__name__)

mqtt.start()
try:
    logging.getLogger("App").info("Starting browser service by default")
    browser.start()
except Exception:
    logging.getLogger("App").exception("Failed to start browser service")

motion.start_motion_thread()


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

host = get_local_ip()
port = 5000
state.stream_url = f"http://{host}:{port}"
mqtt.publish_camera_stream_url(state.stream_url)

@app.route("/settings", methods=["GET", "POST"])
@requires_auth
def settings():
    sensitive_placeholder = "__**password_not_changed**__"

    if request.method == "POST":
        updates = {}
        s = config.current_settings()
        keys = [
            "MOTION_THRESHOLD",
            "INACTIVITY_TIMEOUT",
            "CHECK_INTERVAL",
            "MQTT_HOST",
            "MQTT_PORT",
            "MQTT_TOPIC_PREFIX",
            "MQTT_USERNAME",
            "MQTT_PASSWORD",
            "HASS_DASHBOARD_URL",
        ]

        for key in keys:
            if key in request.form:
                val = request.form.get(key)
                if key == "MOTION_THRESHOLD":
                    try:
                        updates[key] = int(val)
                    except Exception:
                        continue
                elif key in ("INACTIVITY_TIMEOUT", "CHECK_INTERVAL"):
                    try:
                        updates[key] = float(val)
                    except Exception:
                        continue
                elif key == "MQTT_PASSWORD":
                    if val == sensitive_placeholder:
                        continue
                    updates[key] = val or None
                else:
                    updates[key] = val

        if updates:
            config.update_settings(**updates)
            mqtt.start()
        return redirect(url_for("settings"))

    s = config.current_settings()

    pwd_display = sensitive_placeholder if s.get("MQTT_PASSWORD") else ""


    status = {}
    try:
        status['mqtt_connected'] = getattr(mqtt, "_client", None) is not None
        status['mqtt_host'] = s.get('MQTT_HOST')
        status['mqtt_port'] = s.get('MQTT_PORT')
        status['mqtt_topic_prefix'] = s.get('MQTT_TOPIC_PREFIX')
    except Exception:
        logging.getLogger("App").exception("Failed to read MQTT status")

    try:
        ctrl = getattr(browser, "_get_controller")()
        proc = getattr(ctrl, "_proc", None)
        status['browser_running'] = proc is not None and proc.poll() is None
        status['browser_paused'] = getattr(ctrl, "_paused", False)
        status['browser_current_url'] = getattr(ctrl, "current_url", None) or getattr(browser, "get_current_url", lambda: None)()
    except Exception:
        logging.getLogger("App").exception("Failed to read browser status")

    status['motion_event'] = state.motion_event
    status['display_on'] = state.display_on
    status['clients_connected'] = state.clients_connected
    status['stream_url'] = getattr(state, "stream_url", None)

    return render_template('settings.html', s=s, pwd_display=pwd_display, status=status)


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
                if not ret:
                    continue

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg.tobytes()
                    + b"\r\n"
                )
        finally:
            with state.clients_lock:
                state.clients_connected -= 1
                if state.clients_connected == 0:
                    switch_to_lores_mode_if_needed()

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/motion_alerts")
def motion_alerts():
    return ("motion" if state.motion_event else "nomotion"), 200