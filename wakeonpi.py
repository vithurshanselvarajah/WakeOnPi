import os
import time
import threading
import select

import cv2
import numpy as np
from flask import Flask, Response, request, stream_with_context
from picamera2 import Picamera2
from libcamera import Transform
from picamera2.encoders import H264Encoder


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
ignore_motion_until = 0
is_recording = False
recording_lock = threading.Lock()
recording_filename = None

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
    main={"size": (1920, 1080), "format": "RGB888"},
    lores={"size": (320, 180), "format": "YUV420"},
    transform=Transform(vflip=True),
    controls={"FrameRate": 10, "AwbMode": 0}
)

picam2.configure(video_config_lores)
picam2.start()

# --- Switch Modes ---

def switch_to_full_mode():
    global main_stream_active, ignore_motion_until
    with main_stream_lock:
        if not main_stream_active:
            ignore_motion_until = time.time() + 2
            print("Switching to full stream mode")
            picam2.switch_mode(video_config_full)
            main_stream_active = True

def switch_to_lores_mode_if_needed():
    global main_stream_active, ignore_motion_until
    with main_stream_lock:
        if main_stream_active and clients_connected == 0:
            ignore_motion_until = time.time() + 2
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

# --- WebPage ---
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
                frame = cv2.resize(frame, (854, 480), interpolation=cv2.INTER_AREA)
                with frame_lock:
                    current_frame = frame
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if not ret:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        finally:
            with clients_lock:
                clients_connected -= 1
                if clients_connected == 0:
                    switch_to_lores_mode_if_needed()
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/motion_alerts')
def motion_alerts():
    return ('motion' if motion_event else 'nomotion'), 200, {'Content-Type': 'text/plain'}

@app.route('/record')
@requires_auth
def record_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Camera Recorder</title>
        <script>
            function updateStatus() {
                fetch('/record_status')
                .then(response => response.text())
                .then(status => {
                    document.getElementById('status').innerText = status === 'recording' 
                        ? 'Recording in progress' : 'Not recording';
                    document.getElementById('recordBtn').innerText =
                        status === 'recording' ? 'Stop Recording' : 'Start Recording';
                });
            }
            function toggleRecord() {
                fetch('/toggle_record', {method: 'POST'})
                .then(response => response.text())
                .then(msg => {
                    document.getElementById('status').innerText = msg;
                    updateStatus();
                });
            }
            window.onload = updateStatus;
        </script>
    </head>
    <body>
        <h1>Camera Recording</h1>
        <button id="recordBtn" onclick="toggleRecord()">Start Recording</button>
        <p id="status">Checking status...</p>
    </body>
    </html>
    '''

# --- Toggle Recording Endpoint ---
@app.route('/toggle_record', methods=['POST'])
@requires_auth
def toggle_record():
    global is_recording, recording_filename, ignore_motion_until, main_stream_active
    with recording_lock:
        if not is_recording:
            switch_to_full_mode()

            # Setup encoder
            encoder = H264Encoder(bitrate=10000000)
            home_dir = os.path.expanduser("~")
            recording_filename = os.path.join(home_dir, f"video_{int(time.time())}.h264")
            picam2.start_recording(encoder, recording_filename)
            is_recording = True
            return "Recording started"
        else:
            picam2.stop_recording()
            is_recording = False
            ignore_motion_until = time.time() + 2  # prevent false positives

            if clients_connected == 0:
                print("Switching camera back to motion detection mode...")
                picam2.configure(video_config_lores)
                picam2.start()
                main_stream_active = False
            else:
                print("Keeping camera in full stream mode for active viewers...")
                picam2.configure(video_config_full)
                picam2.start()
                main_stream_active = True

            return f"Recording stopped, saved as {recording_filename}"


@app.route('/record_status')
@requires_auth
def record_status():
    return ("recording" if is_recording else "not_recording"), 200, {'Content-Type': 'text/plain'}

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

        if prev_frame is not None and time.time() > ignore_motion_until:
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
        time.sleep(CHECK_INTERVAL)

# --- Start Threads ---
threading.Thread(target=motion_detection_loop, daemon=True).start()

# --- Run Flask Server ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
