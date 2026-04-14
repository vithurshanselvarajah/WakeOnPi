import cv2
import socket
from flask import Flask, Response, stream_with_context, request, redirect, url_for, render_template
import logging
import time

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
            "HTTP_USERNAME",
            "HTTP_PASSWORD",
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
                elif key == "HTTP_PASSWORD":
                    if val == sensitive_placeholder:
                        continue
                    updates[key] = val or None
                else:
                    updates[key] = val

        if updates:
            config.update_settings(**updates)
            try:
                import wakeonpi.motion as motion_mod
                motion_mod.config = config
            except Exception:
                pass
            try:
                mqtt.restart()
            except Exception:
                logging.getLogger("App").exception("Failed to restart MQTT after settings change")
        return redirect(url_for("settings"))

    s = config.current_settings()
    pwd_display = sensitive_placeholder if s.get("MQTT_PASSWORD") else ""
    http_pwd_display = sensitive_placeholder if s.get("HTTP_PASSWORD") else ""

    status = {}
    try:
        status['mqtt_connected'] = getattr(mqtt, "is_connected", lambda: False)()
        status['mqtt_host'] = s.get('MQTT_HOST')
        status['mqtt_port'] = s.get('MQTT_PORT')
        status['mqtt_topic_prefix'] = config.MQTT_TOPIC_PREFIX
    except Exception:
        logging.getLogger("App").exception("Failed to read MQTT status")

    try:
        ctrl = getattr(browser, "_get_controller")()
        proc = getattr(ctrl, "_proc", None)
        browser_running = proc is not None and proc.poll() is None
        status['browser_running'] = browser_running
        status['browser_current_url'] = getattr(ctrl, "current_url", None) or getattr(browser, "get_current_url", lambda: None)() or s.get("HASS_DASHBOARD_URL")
    except Exception:
        logging.getLogger("App").exception("Failed to read browser status")

    status['motion_event'] = state.motion_event
    status['display_on'] = state.display_on
    status['clients_connected'] = state.clients_connected
    status['stream_url'] = getattr(state, "stream_url", None)
    try:
        version = mqtt.get_system_version()
        status['version'] = version or 'N/A'
    except Exception:
        status['version'] = 'N/A'

    return render_template('settings.html', s=s, pwd_display=pwd_display, http_pwd_display=http_pwd_display, status=status)


@app.route('/settings/mqtt/reconnect', methods=['POST'])
@requires_auth
def settings_mqtt_reconnect():
    try:
        mqtt.restart()
        return ('', 204)
    except Exception:
        logging.getLogger("App").exception("Failed to reconnect MQTT")
        return ('Error', 500)


@app.route('/settings/browser/refresh', methods=['POST'])
@requires_auth
def settings_browser_refresh():
    try:
        import wakeonpi.browser as browser
        browser.refresh()
        return ('', 204)
    except Exception:
        logging.getLogger("App").exception("Failed to refresh browser")
        return ('Error', 500)


@app.route('/settings/restart', methods=['POST'])
@requires_auth
def settings_restart():
    try:
        mqtt.restart()
        try:
            import wakeonpi.browser as browser
            browser.stop()
            browser.start()
        except Exception:
            logging.getLogger("App").exception("Failed to restart browser during full restart")
        return ('', 204)
    except Exception:
        logging.getLogger("App").exception("Failed to restart services")
        return ('Error', 500)

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