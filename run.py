from wakeonpi.app import app
from wakeonpi.motion import start_motion_thread

if __name__ == "__main__":
    start_motion_thread()
    app.run(host="0.0.0.0", port=5000, threaded=True)