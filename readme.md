# WakeOnPi

WakeOnPi is a small, motion-aware camera streaming service for the Raspberry Pi 5. It is designed to work well with the official Raspberry Pi Touch Display 2 and provides a live MJPEG stream that automatically turns the display on when motion is detected and off after a period of inactivity.

Key points:

- Motion detection is performed on low-resolution YUV frames for efficiency.
- The camera switches to a higher-resolution stream only while clients are connected.
- The touch display's backlight is controlled via sysfs to save power and extend display life.
- Basic HTTP authentication protects the stream and settings pages.
- Optional MQTT integration can publish motion, display state and the stream URL, and accept simple display control commands.

---

## Features

- MJPEG live stream served over HTTP (default port 5000)
- Low-res motion detection with configurable sensitivity and timeouts
- Automatic display on/off using `/sys/class/backlight/10-0045/bl_power` (Touch Display 2)
- Settings UI at `/settings` (protected by basic auth)
- Motion state endpoint at `/motion_alerts` (returns `motion` or `nomotion`)
- MQTT support (publish/subscribe) when `paho-mqtt` is installed

---

## Quick start

### 1. Prepare the Raspberry Pi

- Enable the camera and libcamera support on your Pi (raspi-config or the appropriate setup for your OS).
- If you plan to control the touch display backlight, make sure the sysfs path used here exists on your device: `/sys/class/backlight/10-0045/bl_power`.

### 2. Install Python dependencies

On the Pi, install required packages. The project uses Python and these libraries:

- Flask
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

- `/settings` — small web UI to adjust values (MOTION_THRESHOLD, INACTIVITY_TIMEOUT, CHECK_INTERVAL, MQTT settings). Protected by the same basic auth.
- `/motion_alerts` — returns `motion` or `nomotion` depending on the current detected state.
- The main stream served at `/` is an MJPEG multipart response suitable for browser preview or apps that support MJPEG.

---

## Configuration

The application stores runtime settings in `wakeonpi/settings.json` and exposes defaults in `wakeonpi/config.py`. Default values include:

- MOTION_THRESHOLD: 1500
- INACTIVITY_TIMEOUT: 15 (seconds)
- CHECK_INTERVAL: 1.0 (seconds)
- MQTT_TOPIC_PREFIX: `wakeonpi`

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

- Publish motion state: `<prefix>/motion` with `ON`/`OFF`
- Publish display state: `<prefix>/screen` with `ON`/`OFF`
- Publish stream URL: `<prefix>/stream_url`
- Subscribe to `<prefix>/screen/set` to accept `on`/`off`/`1`/`0`/`true` values which will toggle the display. When a message is received the display is set and a manual display override is engaged briefly.

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
