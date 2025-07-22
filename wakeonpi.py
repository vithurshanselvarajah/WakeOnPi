import os
import time
import threading
import select

import cv2
import numpy as np
from flask import Flask, render_template_string, Response, request, stream_with_context
from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput
from libcamera import Transform


# --- Config ---
MOTION_THRESHOLD = 1500  # Tune for sensitivity
INACTIVITY_TIMEOUT = 15  # Seconds until screen turns off
CHECK_INTERVAL = 1.0     # Seconds between motion checks

# --- Globals ---
motion_event = False
last_motion_time = 0
current_frame = None
frame_lock = threading.Lock()
display_on = True
clients_connected = 0
clients_lock = threading.Lock()
main_stream_active = False
main_stream_lock = threading.Lock()

# --- Authentication Credentials ---
USERNAME = os.environ.get("MOTION_USERNAME")
PASSWORD = os.environ.get("MOTION_PASSWORD")


# --- Initialize Camera ---
picam2 = Picamera2()

# Low-res only config (for motion detection)
video_config_lores = picam2.create_video_configuration(
    lores={"size": (320, 180), "format": "YUV420"},
    transform=Transform(vflip=True),
    controls={"FrameRate": 2, "AwbMode": 0}
)

# Full-res config (for streaming)
video_config_full = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "RGB888"},
    lores={"size": (320, 180), "format": "YUV420"},
    transform=Transform(vflip=True),
    controls={"FrameRate": 2, "AwbMode": 0}
)

picam2.configure(video_config_lores)
picam2.start()

# --- Switch Modes ---

def switch_to_full_mode():
    global main_stream_active
    with main_stream_lock:
        if not main_stream_active:
            print("Switching to full stream mode")
            picam2.switch_mode(video_config_full)
            main_stream_active = True

def switch_to_lores_mode_if_needed():
    global main_stream_active
    with main_stream_lock:
        if main_stream_active and clients_connected == 0:
            print("Switching back to lores mode")
            picam2.switch_mode(video_config_lores)
            main_stream_active = False


# --- Authentication ---
def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__  # Needed to avoid Flask route warnings
    return decorated

# --- Flask App ---
app = Flask(__name__)

@app.route('/')
@requires_auth
def video_feed():
    global clients_connected
    @stream_with_context
    def gen():
        global current_frame, clients_connected
        with clients_lock:
            clients_connected += 1
        switch_to_full_mode()
        try:
            while True:
                frame = picam2.capture_array("main")
                with frame_lock:
                    current_frame = frame
                ret, jpeg = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        finally:
            with clients_lock:
                clients_connected -= 1
                switch_to_lores_mode_if_needed()
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/motion_alerts')
def motion_alerts():
    return ('motion' if motion_event else 'nomotion'), 200, {'Content-Type': 'text/plain'}

# --- Display Control ---
def set_display(state):
    try:
        with open("/sys/class/backlight/11-0045/bl_power", "w") as f:
            f.write("0" if state else "1")
    except Exception as e:
        print(f"Failed to change display power: {e}")


# --- Motion Detection Thread ---
def motion_detection_loop():
    global motion_event, last_motion_time, display_on
    prev_frame = None

    def set_display_if_needed(state):
        global display_on
        if state != display_on:
            set_display(state)
            display_on = state

    while True:
        lores_frame = picam2.capture_array("lores")
        # Efficient Y (grayscale) extraction from YUV420 frame
        gray = lores_frame[:lores_frame.shape[0] // 3, :].copy()
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if prev_frame is not None:
            delta = cv2.absdiff(prev_frame, gray)
            _, thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
            motion_score = cv2.countNonZero(thresh)

            if motion_score > MOTION_THRESHOLD:
                last_motion_time = time.time()
                set_display_if_needed(True)
                motion_event = True
            elif time.time() - last_motion_time > INACTIVITY_TIMEOUT:
                set_display_if_needed(False)
                motion_event = False

        prev_frame = gray
        select.select([], [], [], CHECK_INTERVAL)

# --- Start Threads ---
threading.Thread(target=motion_detection_loop, daemon=True).start()

# --- Run Flask Server ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
