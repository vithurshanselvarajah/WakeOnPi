# WakeOnPi

WakeOnPi is a small, motion-aware camera streaming service for the Raspberry Pi 5. It is designed to work well with the official Raspberry Pi Touch Display 2 and provides a live MJPEG stream that automatically turns the display on when motion is detected and off after a period of inactivity.

Key points:

- Motion detection is performed on low-resolution YUV frames for efficiency.
- The camera switches to a higher-resolution stream only while clients are connected.
- The touch display's backlight is controlled via sysfs to save power and extend display life.
- Display brightness control for Touch Display 2.
- Basic HTTP authentication protects the stream and settings pages.
- Optional MQTT integration with auto-reconnect and full Home Assistant discovery.
- Real-time WebSocket-based settings page with system monitoring.
- Customizable stream overlay with time, stats, and notifications.

---

## Features

- MJPEG live stream served over HTTP (default port 5000)
- Snapshot endpoint at `/snapshot` for single frame capture
- Low-res motion detection with configurable sensitivity and timeouts
- Automatic display on/off using `/sys/class/backlight/10-0045/bl_power` (Touch Display 2)
- Display brightness control (5-100%)
- Adjustable stream resolution, FPS, and quality
- System overlay with time, stats, and custom notifications
- Modern WebSocket-based settings UI at `/settings` (mobile-friendly)
- Health check endpoint at `/health` with system stats
- Motion state endpoint at `/motion_alerts` (returns `motion` or `nomotion`)
- MQTT support with auto-reconnect and exponential backoff
- Full Home Assistant MQTT auto-discovery
- Real-time system stats: CPU temp, usage, memory, storage
- Storage free space monitoring and reporting

---

## Quick start

### 1. Prepare the Raspberry Pi

- Enable the camera and libcamera support on your Pi (raspi-config or the appropriate setup for your OS).
- If you plan to control the touch display backlight, make sure the sysfs path used here exists on your device: `/sys/class/backlight/10-0045/bl_power`.

### 2. Install Python dependencies

On the Pi, install required packages. The project uses Python and these libraries:

- Flask
- Flask-Sock (WebSocket support)
- OpenCV (cv2)
- picamera2
- paho-mqtt (optional, required only if you want MQTT)

Example (Raspberry Pi OS):

```bash
sudo apt update; sudo apt install -y python3-pip libatlas-base-dev libjpeg-dev
python3 -m pip install -r requirements.txt
```

### 3. Set credentials and run

The application uses HTTP Basic auth. Provide credentials via environment variables:

- MOTION_USERNAME
- MOTION_PASSWORD

Example (temporary run):

```bash
sudo MOTION_USERNAME=your_username MOTION_PASSWORD=your_password python3 run.py
```

Note: sudo may be required to access the camera device and to write to the backlight sysfs file.

### 4. Open the stream

Open a browser to:

```
http://<raspberry-pi-ip>:5000/
```

Log in with the username and password you set.

---

## Settings and endpoints

- `/` — MJPEG live stream (protected by basic auth)
- `/settings` — Modern WebSocket-based settings UI with real-time updates (protected by basic auth)
- `/snapshot` — Single JPEG frame capture (protected by basic auth)
- `/health` — JSON health check with system stats (no auth required)
- `/motion_alerts` — Returns `motion` or `nomotion` (no auth required)
- `/api/status` — JSON status endpoint (protected by basic auth)
- `/api/settings` — GET/POST settings via JSON (protected by basic auth)
- `/api/display` — POST to control display on/off and brightness (protected by basic auth)
- `/api/overlay/notify` — POST to send overlay notifications (protected by basic auth)
- `/ws` — WebSocket endpoint for real-time updates

---

## Configuration

The application stores runtime settings in `wakeonpi/settings.json` and exposes defaults in `wakeonpi/config.py`. Default values include:

- MOTION_THRESHOLD: 1500
- INACTIVITY_TIMEOUT: 60 (seconds)
- CHECK_INTERVAL: 1.0 (seconds)
- STREAM_RESOLUTION: 854x480
- STREAM_FPS: 10
- STREAM_QUALITY: 75
- MQTT_TOPIC_PREFIX: `wakeonpi`
- OVERLAY_ENABLED: true
- OVERLAY_SHOW_TIME: true
- OVERLAY_SHOW_STATS: false
- OVERLAY_POSITION: top-right

You can edit these values either in the `settings.json` file or via the `/settings` web UI.

---

## Running as a systemd service

Create a unit file such as `/etc/systemd/system/wakeonpi.service`:

```
[Unit]
Description=WakeOnPi - motion-aware camera stream and display controller
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/WakeOnPi/run.py
WorkingDirectory=/home/pi/WakeOnPi
Environment=MOTION_USERNAME=your_username
Environment=MOTION_PASSWORD=your_password
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload; sudo systemctl enable wakeonpi; sudo systemctl start wakeonpi
```

---

## MQTT integration

If `paho-mqtt` is installed and MQTT settings are configured in the `/settings` UI or `wakeonpi/settings.json`, WakeOnPi will:

**Published topics (state):**
- `<prefix>/state/motion` — `ON`/`OFF`
- `<prefix>/state/screen` — `ON`/`OFF`
- `<prefix>/state/screen/brightness` — 5-100
- `<prefix>/state/camera/stream_url` — Stream URL
- `<prefix>/state/browser/url` — Current browser URL
- `<prefix>/state/recording/active` — `ON`/`OFF`
- `<prefix>/state/system/version` — Version string
- `<prefix>/state/system/cpu_temp` — CPU temperature in °C
- `<prefix>/state/system/cpu_usage` — CPU usage percentage
- `<prefix>/state/system/memory_percent` — Memory usage percentage
- `<prefix>/state/system/uptime` — Uptime in seconds
- `<prefix>/state/storage/free_gb` — Free storage in GB
- `<prefix>/state/storage/used_percent` — Storage used percentage
- `<prefix>/state/clients_connected` — Number of connected stream viewers
- `<prefix>/state/availability` — `online`/`offline`

**Command topics (subscribe):**
- `<prefix>/command/screen/set` — `on`/`off`/`1`/`0`/`true`/`false`
- `<prefix>/command/screen/brightness` — 5-100
- `<prefix>/command/browser/url_set` — URL to navigate to
- `<prefix>/command/browser/refresh` — Any payload refreshes browser
- `<prefix>/command/recording/toggle` — Any payload toggles recording
- `<prefix>/command/overlay/notify` — JSON `{"message": "text", "duration": 5}` or plain text

**Home Assistant Auto-Discovery:**
WakeOnPi automatically publishes MQTT discovery messages for Home Assistant, creating:
- Binary sensor for motion detection
- Switch for screen on/off
- Number for brightness control
- Sensors for CPU temp, usage, memory, storage, uptime, version
- Text entity for browser URL control
- Button for browser refresh
- Switch for recording toggle
- Camera entity for the MJPEG stream

MQTT auto-reconnect is enabled with exponential backoff (5s to 5min).

By default the MQTT prefix is `wakeonpi`.

---

## Troubleshooting

- If the stream is blank or the camera fails to start, ensure libcamera and picamera2 are properly installed and working on your system.
- If backlight control fails, check permissions and whether the sysfs path exists on your hardware. The code writes `0` (on) and `1` (off) to `/sys/class/backlight/10-0045/bl_power`.
- If MQTT does not connect, verify the broker host/port and credentials. If `paho-mqtt` is not installed the project will continue to run with MQTT disabled.

---

## Security notes

- The simple Basic Auth implementation uses plain credentials from environment variables. Run behind a trusted network or reverse proxy with TLS if exposing the service outside your local network.

---

## License

This repository is provided under a non-commercial license: you are free to use, modify and share the project for non-commercial purposes only. For commercial use please contact the author to discuss licensing.

---
