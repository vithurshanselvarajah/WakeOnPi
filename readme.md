# WakeOnPi

WakeOnPi is a Raspberry Pi camera service that combines motion detection, MJPEG streaming, screen control, and optional MQTT/Home Assistant integration.

It is built for always-on Pi setups where you want the display and stream to react to motion without wasting power.

## What it does

- Detects motion from low-resolution camera frames.
- Streams live MJPEG at `/stream`.
- Captures snapshots at `/snapshot`.
- Controls display power and brightness through sysfs backlight paths.
- Offers a real-time settings UI at `/settings` (authenticated with cookie sessions and a custom login page).
- Publishes state and accepts commands over MQTT (including Home Assistant auto-discovery for binary sensors, switches, numbers, and native update platform).
- Supports manual and motion-triggered recording.
- Self-update mechanism triggered via WebUI or Home Assistant.

## Quick start

1. Install dependencies via `apt` (and the remaining `flask-sock` package via `pip`):

```bash
sudo apt update
sudo apt install -y python3-flask python3-paho-mqtt python3-opencv python3-picamera2 python3-pip
sudo pip3 install flask-sock --break-system-packages
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

- `GET /setup` - First-time setup wizard (create admin account)
- `GET /login` / `/logout` - WebUI session management (redirects to `/setup` if no account exists)
- `GET /settings` - settings dashboard (session auth)
- `GET /stream` - MJPEG stream (stream basic auth or session auth)
- `GET /snapshot` - single JPEG frame (stream basic auth or session auth)
- `GET /health` - health and system stats
- `GET /motion_alerts` - `motion` or `nomotion`
- `GET /api/status` - full runtime status (session auth)
- `GET/POST /api/settings` - read/update settings (session auth)
- `POST /api/display` - display on/off and brightness (session auth)
- `GET /api/logs` - recent in-memory logs (session auth)
- `POST /api/update/check` / `POST /api/update/install` - version checking and updates (session auth)
- `WS /ws` - live status updates and control events

## Configuration

The application now stores all configuration in an internal SQLite database (`wakeonpi.db`). Default configuration values are loaded from `wakeonpi/settings_template.json` and ingested into the SQLite database on first launch. Users configure the system through the web UI.

On first launch, **no admin account exists**. Navigating to any URL (including `/login` or `/settings`) automatically redirects to the **Setup Wizard** at `/setup`, where you create an admin username and password. Until this step is completed, the login page and all protected endpoints remain inaccessible. These credentials are stored as salted PBKDF2 hashes in the database.

Key configuration points:

- **Database**: `wakeonpi/db.py` manages the SQLite file located at `wakeonpi/wakeonpi.db`. It contains tables for settings and user credentials.
- **First-Connection Setup**: On first run, if no admin account exists, every page redirects to `/setup`. The wizard asks for an admin username and password, which are saved securely (PBKDF2 hash). After setup, normal login and operation resumes.
- **Stream Authentication**: Stream endpoints (`/stream`, `/snapshot`) continue to support Basic Auth with a generated random password, visible and resettable via the Settings UI.
- **Home Assistant Integration**: The update mechanism is exposed via Home Assistant using the native update platform. Updates can be triggered from Home Assistant or the Web UI.
- **Other Settings**: Remaining runtime options (motion thresholds, display control, MQTT broker, etc.) are still accessible via the Settings page and are persisted in the SQLite database.

## Notes

- This project is designed for Linux on Raspberry Pi (uses `picamera2`, `/proc`, and `/sys/class/backlight/...`).
- Camera and backlight access may require elevated permissions depending on your setup.
- WebUI endpoints use session-based cookie authentication using a session secret key.
- Stream endpoints (`/stream` and `/snapshot`) support Basic Auth using the username `stream` and a randomly generated password, visible and resettable via the WebUI.
- Updates download and extract the latest release from GitHub, then trigger an in-place Python process reload without requiring root/sudo privileges.
- MQTT is optional; if unavailable, the app still runs without it.

## Development

To reset the application state during development, you can delete the SQLite database file:
```powershell
Remove-Item -Force "wakeonpi/wakeonpi.db"
```
The file is ignored by Git via `.gitignore`.
