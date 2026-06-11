# Configuration Guide

WakeOnPi stores all system configuration and administrative credentials in an internal SQLite database (`wakeonpi.db`) located in the package directory. Setting values are persisted automatically across reboots and process restarts.

---

## Initial Setup Flow

On first launch, WakeOnPi detects if the database is unconfigured. Visiting any endpoint will redirect you to the **Setup Wizard** at `/setup`.

1. **Create Administrator Account**: Enter your desired admin username and a secure password.
2. **Persistence**: These credentials are saved as salted PBKDF2 hashes in the database.
3. **Session Authentication**: Logging in at `/login` provides a browser cookie session to access the dashboard.

---

## Settings Dashboard

The Settings Dashboard at `/settings` provides an interactive interface to configure the following areas at runtime:

### 1. Display Control
- **SCREEN_CONTROL_MODE**:
  - `auto`: Power screen on/off based on motion detection.
  - `always_on`: Keep screen powered on continuously.
  - `always_off`: Keep screen powered off continuously.
- **BACKLIGHT_PATH**: Sysfs path controlling display power (e.g., `/sys/class/backlight/rpi_backlight/bl_power`).
- **BRIGHTNESS_PATH**: Sysfs path controlling display brightness (e.g., `/sys/class/backlight/rpi_backlight/brightness`).
- **INACTIVITY_TIMEOUT**: Inactivity delay (seconds) before powering off the screen when mode is `auto`.

### 2. Motion Detection
- **MOTION_THRESHOLD**: Motion sensitivity threshold (lower values make the detection more sensitive).
- **CHECK_INTERVAL**: Delay (seconds) between camera frames checked for motion.

### 3. Camera & Streaming
- **STREAM_RESOLUTION**: Streaming video feed size (e.g., `854x480`, `1280x720`).
- **STREAM_FPS**: Target frames-per-second.
- **STREAM_QUALITY**: JPEG compression quality (1-100).
- **STREAM_PASSWORD**: Randomly generated basic authentication password for `/stream` and `/snapshot`.

### 4. Recordings
- **RECORD_ON_MOTION**: Enable automated video recording upon motion detection.
- **RECORD_POST_MOTION_TIMEOUT**: Duration (seconds) to continue recording after motion has stopped.
- **STORAGE_MAX_PERCENT**: Disk space threshold before executing storage actions.
- **STORAGE_FULL_ACTION**: Action when disk is full (`pause` or `overwrite`).

### 5. MQTT & Home Assistant
- **MQTT_HOST**: Broker IP address or hostname.
- **MQTT_PORT**: Port number (default: `1883`).
- **MQTT_USERNAME** / **MQTT_PASSWORD**: Credentials for MQTT authentication.
- **MQTT_TOPIC_PREFIX**: Base topic prefix for all state and command topics.
- **UPDATE_CHANNEL**: Release channel (`release` or `beta`) for automatic updates.

---

## MQTT Topics & Integration

### State Topics (Published by WakeOnPi)
```
<prefix>/state/availability         - Client availability ("online" / "offline")
<prefix>/state/motion               - Motion sensor state ("ON" / "OFF")
<prefix>/state/screen               - Display power state ("ON" / "OFF")
<prefix>/state/screen/brightness    - Display brightness level (5-100)
<prefix>/state/screen/mode          - Control mode ("auto" / "always_on" / "always_off")
<prefix>/state/recording/active     - Recording state ("ON" / "OFF")
<prefix>/state/system/ip            - Local IP address
<prefix>/state/update               - Update availability status (JSON payload)
```

### Command Topics (Subscribed by WakeOnPi)
```
<prefix>/command/screen/set         - Set screen power ("ON" / "OFF")
<prefix>/command/screen/brightness  - Set screen brightness (5-100)
<prefix>/command/screen/mode        - Change screen mode ("auto", "always_on", "always_off")
<prefix>/command/browser/url_set    - Launch/redirect browser to URL
<prefix>/command/browser/refresh    - Refresh current browser page
<prefix>/command/recording/toggle   - Start/stop recording
<prefix>/command/update/install     - Install available firmware update ("install")
```

---

## Home Assistant Native Update Platform

If MQTT is configured, WakeOnPi publishes Home Assistant Discovery metadata to integrate directly with the native Home Assistant Update entity.

- **Check Updates**: Done automatically in the background.
- **Trigger Installation**: Trigger update installation directly via the Home Assistant card or the `/settings/update` interface.
- **Rollbacks**: If an update breaks compatibility, you can roll back to a previously installed version via the rollback page in the WebUI.
