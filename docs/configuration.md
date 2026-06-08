# Configuration Guide

## Environment Variables

WakeOnPi is configured via environment variables. Create a `.env` file in the project root or set them in your environment.

### Authentication

```env
# Basic authentication credentials
AUTH_USERNAME=admin
AUTH_PASSWORD=your_secure_password_here

# Session timeout (seconds)
SESSION_TIMEOUT=3600
```

### MQTT Configuration

```env
# MQTT Broker settings
MQTT_ENABLED=true
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password

# Topic prefix for all published topics
MQTT_TOPIC_PREFIX=wakeonpi

# Home Assistant Discovery (optional)
MQTT_HA_DISCOVERY=true
MQTT_HA_PREFIX=homeassistant
```

### Display Configuration

```env
# Path to brightness control (sysfs)
DISPLAY_BRIGHTNESS_PATH=/sys/class/backlight/rpi_backlight/brightness

# Path to max brightness file
DISPLAY_MAX_BRIGHTNESS_PATH=/sys/class/backlight/rpi_backlight/max_brightness

# Default brightness level (0-100)
DISPLAY_DEFAULT_BRIGHTNESS=100

# Auto-off timeout in seconds (0 = disabled)
DISPLAY_AUTO_OFF_TIMEOUT=600
```

### Camera Configuration

```env
# Camera rotation in degrees (0, 90, 180, 270)
CAMERA_ROTATION=0

# Camera resolution (width x height)
CAMERA_RESOLUTION=1280x720

# Frame rate (fps)
CAMERA_FRAMERATE=30

# Camera flip (horizontal/vertical)
CAMERA_HFLIP=false
CAMERA_VFLIP=false
```

### Motion Detection

```env
# Motion detection sensitivity (0.0-100.0, lower = more sensitive)
MOTION_THRESHOLD=5.0

# Minimum area for motion detection (pixels)
MOTION_MIN_AREA=500

# Debounce time (seconds) to avoid rapid toggles
MOTION_DEBOUNCE_TIME=2

# Enable motion detection
MOTION_ENABLED=true
```

### Recording Configuration

```env
# Recording directory
RECORDING_DIR=./recordings

# Maximum recording file size (MB)
RECORDING_MAX_SIZE=500

# Recording quality (1-51, lower = better)
RECORDING_QUALITY=23

# Enable auto-recording on motion
RECORDING_AUTO_ON_MOTION=true
```

### Application Settings

```env
# Flask debug mode (disable in production)
FLASK_DEBUG=false

# Flask host and port
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Log file path (empty = stdout only)
LOG_FILE=/var/log/wakeonpi/app.log
```

## Settings Dashboard

The settings dashboard at `/settings` provides a web-based interface to modify configuration at runtime. Changes made through the dashboard are persisted to disk.

### Available Settings

- **Display**: Power state, brightness level, auto-off timeout
- **Motion Detection**: Enable/disable, sensitivity, debounce settings
- **Recording**: Enable/disable, quality, storage location
- **Stream**: Resolution, frame rate
- **MQTT**: Broker settings, topic prefix
- **System**: Restart service, view logs

## MQTT Topics

### Published Topics

```
<prefix>/status        - Full JSON status (online/offline)
<prefix>/motion        - Motion detection state (motion/nomotion)
<prefix>/display/power - Display power state (on/off)
<prefix>/display/brightness - Current brightness (0-100)
<prefix>/recording     - Recording state (recording/stopped)
<prefix>/stream        - Stream availability (active/inactive)
```

### Subscribed Topics

```
<prefix>/command/display/on     - Turn display on
<prefix>/command/display/off    - Turn display off
<prefix>/command/display/brightness - Set brightness (0-100)
<prefix>/command/record/start   - Start recording
<prefix>/command/record/stop    - Stop recording
```

## Home Assistant Integration

WakeOnPi automatically publishes MQTT Discovery messages for Home Assistant integration when `MQTT_HA_DISCOVERY=true`.

### Available Entities

- **Binary Sensor**: Motion detection state
- **Switch**: Display power control
- **Light**: Display brightness control
- **Camera**: MJPEG stream feed
- **Sensor**: System stats (CPU, memory, temperature)

## Advanced Configuration

### Custom Backlight Path

Find your backlight path:

```bash
ls /sys/class/backlight/
```

Common paths:
- Raspberry Pi 7" Touchscreen: `/sys/class/backlight/rpi_backlight/`
- Generic display: `/sys/class/backlight/[your-display]/`

### Performance Tuning

For better performance on Pi Zero:

```env
CAMERA_RESOLUTION=640x480
CAMERA_FRAMERATE=15
MOTION_THRESHOLD=10.0
```

For higher quality on Pi 4:

```env
CAMERA_RESOLUTION=1920x1080
CAMERA_FRAMERATE=60
MOTION_THRESHOLD=3.0
```

### Security

- Always use strong passwords
- Change default credentials before deployment
- Use HTTPS in production (via reverse proxy)
- Restrict MQTT broker access
- Enable authentication for all endpoints

## Troubleshooting Configuration

### Settings not persisting
- Check file permissions in data directory
- Verify disk space availability
- Review application logs for errors

### MQTT not connecting
- Verify broker is accessible: `telnet <broker> 1883`
- Check credentials in `.env` file
- Review MQTT logs on broker

### Display control not working
- Verify backlight path exists
- Check file permissions
- Ensure user has access to `/sys/class/backlight/`

For more help, see [Installation Guide](./installation.md) troubleshooting section.
