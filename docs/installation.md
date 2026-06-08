# Installation Guide

## Prerequisites

- Raspberry Pi (3, 4, or 5 recommended) running Raspberry Pi OS or similar Linux distribution
- Python 3.7 or higher
- Camera module connected and enabled
- pip (Python package manager)

## System Dependencies

Before installing Python dependencies, install required system packages:

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libjasper1 \
    libharfbuzz0b \
    libwebp6 \
    libtk8.6 \
    libopenjp2-7 \
    libopenjp2-7-dev \
    libjasper-dev \
    libopenblas-dev
```

## Camera Setup

Ensure your camera is enabled:

```bash
sudo raspi-config
```

Navigate to `Interface Options` → `Camera` and enable it.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/WakeOnPi.git
cd WakeOnPi
```

2. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with your settings:

```env
# Authentication
AUTH_USERNAME=admin
AUTH_PASSWORD=your_secure_password

# MQTT (optional)
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password
MQTT_TOPIC_PREFIX=wakeonpi

# Display
DISPLAY_BRIGHTNESS_PATH=/sys/class/backlight/rpi_backlight/brightness
DISPLAY_MAX_BRIGHTNESS_PATH=/sys/class/backlight/rpi_backlight/max_brightness

# Camera
CAMERA_ROTATION=0
CAMERA_FRAMERATE=30

# Motion Detection
MOTION_THRESHOLD=5.0
MOTION_MIN_AREA=500
```

## Running WakeOnPi

```bash
python3 run.py
```

The application will start on `http://localhost:5000`

Access the settings dashboard at:
```
http://<your-pi-ip>:5000/settings
```

## Running as a Service

To run WakeOnPi on startup, create a systemd service file:

```bash
sudo nano /etc/systemd/system/wakeonpi.service
```

Add the following:

```ini
[Unit]
Description=WakeOnPi - Raspberry Pi Camera Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/WakeOnPi
ExecStart=/home/pi/WakeOnPi/venv/bin/python3 run.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable wakeonpi
sudo systemctl start wakeonpi
```

Check status:

```bash
sudo systemctl status wakeonpi
```

## Troubleshooting

### Camera not detected
- Verify camera is connected and enabled via `raspi-config`
- Check camera permissions: `ls -la /dev/video*`

### Permission errors
- Ensure the user running WakeOnPi has permission to access camera and display
- Add user to required groups: `sudo usermod -a -G video,gpio pi`

### Display control not working
- Verify backlight path exists: `ls /sys/class/backlight/`
- Check permissions for backlight control

For more help, refer to the main repository issues.
