# WakeOnPi

WakeOnPi is a Raspberry Pi camera service that combines motion detection, MJPEG streaming, screen control, and optional MQTT/Home Assistant integration.

It is built for always-on Pi setups where you want the display and stream to react to motion without wasting power.

## What it does

- Detects motion from low-resolution camera frames.
- Streams live MJPEG at `/stream`.
- Captures snapshots at `/snapshot`.
- Controls display power and brightness through sysfs backlight paths.
- Offers a real-time settings UI at `/settings` (WebSocket-based).
- Publishes state and accepts commands over MQTT (with Home Assistant discovery).
- Supports manual and motion-triggered recording.

## Quick start

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Run the app:

```bash
python3 run.py
```

3. Open:

```text
http://<pi-ip>:5000/settings
http://<pi-ip>:5000/stream
```

## Main endpoints

- `GET /settings` - settings dashboard (auth)
- `GET /stream` - MJPEG stream (auth)
- `GET /snapshot` - single JPEG frame (auth)
- `GET /health` - health and system stats
- `GET /motion_alerts` - `motion` or `nomotion`
- `GET /api/status` - full runtime status (auth)
- `GET/POST /api/settings` - read/update settings (auth)
- `POST /api/display` - display on/off and brightness (auth)
- `GET /api/logs` - recent in-memory logs (auth)
- `WS /ws` - live status updates and control events

## Configuration

Runtime settings are stored in `wakeonpi/settings.json` (defaults in `wakeonpi/config.py`).

Most configuration is expected to be done from `/settings`, including:

- Motion thresholds and inactivity timeout
- Stream resolution, FPS, and JPEG quality
- Display paths and brightness control
- MQTT broker and topic prefix
- Recording and storage behavior
- Screen mode: `auto`, `always_on`, `always_off`

## Notes

- This project is designed for Linux on Raspberry Pi (uses `picamera2`, `/proc`, and `/sys/class/backlight/...`).
- Camera and backlight access may require elevated permissions depending on your setup.
- HTTP endpoints use Basic Auth configured in settings (`HTTP_USERNAME` / `HTTP_PASSWORD`).
- MQTT is optional; if unavailable, the app still runs without it.
