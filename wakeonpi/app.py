import cv2
import socket
from flask import Flask, Response, stream_with_context, request, redirect, url_for
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
mqtt.publish_stream_url(state.stream_url)

@app.route("/settings", methods=["GET", "POST"])
@requires_auth
def settings():
    if request.method == "POST":
        updates = {}
        for key in ("MOTION_THRESHOLD", "INACTIVITY_TIMEOUT", "CHECK_INTERVAL", "MQTT_HOST", "MQTT_PORT", "MQTT_TOPIC_PREFIX"):
            if key in request.form:
                val = request.form[key]
                if key in ("MOTION_THRESHOLD",):
                    val = int(val)
                elif key in ("INACTIVITY_TIMEOUT", "CHECK_INTERVAL"):
                    val = float(val)
                updates[key] = val
        config.update_settings(**updates)
        mqtt.start()
        return redirect(url_for("settings"))

    s = config.current_settings()
    return (
        f"<h1>WakeOnPi Settings</h1>"
        f"<form method='post'>"
        f"MOTION_THRESHOLD: <input name='MOTION_THRESHOLD' value='{s['MOTION_THRESHOLD']}'/><br/>"
        f"INACTIVITY_TIMEOUT: <input name='INACTIVITY_TIMEOUT' value='{s['INACTIVITY_TIMEOUT']}'/><br/>"
        f"CHECK_INTERVAL: <input name='CHECK_INTERVAL' value='{s['CHECK_INTERVAL']}'/><br/>"
        f"MQTT_HOST: <input name='MQTT_HOST' value='{s['MQTT_HOST'] or ''}'/><br/>"
        f"MQTT_PORT: <input name='MQTT_PORT' value='{s['MQTT_PORT']}'/><br/>"
        f"MQTT_TOPIC_PREFIX: <input name='MQTT_TOPIC_PREFIX' value='{s['MQTT_TOPIC_PREFIX']}'/><br/>"
        f"<button type='submit'>Save</button>"
        f"</form>"
    )

@app.route("/display", methods=["POST"])
@requires_auth
def api_display():
    val = request.form.get("on", "").lower() in ("1", "true", "on")
    set_display = __import__("wakeonpi.display", fromlist=["set_display"]).set_display
    set_display(val)
    state.display_on = val
    mqtt.publish_display(val)
    return ("OK", 200)

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