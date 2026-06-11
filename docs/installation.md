# Installation Guide

## Prerequisites

- Raspberry Pi (3, 4, or 5 recommended) running Raspberry Pi OS or similar Linux distribution.
- Python 3.14 or later.
- Camera module connected and enabled.
- pip (Python package manager).

---

## System Dependencies

Before installing Python dependencies, install the required system packages:

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
    libopenblas-dev
```

---

## Camera Setup

Ensure your Raspberry Pi camera interface is enabled:

```bash
sudo raspi-config
```

Navigate to `Interface Options` → `Camera` and select `Yes` to enable it, then reboot.

---

## Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/vithurshanselvarajah/WakeOnPi.git
   cd WakeOnPi
   ```

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running WakeOnPi

Start the application using the entry point:

```bash
python3 run.py
```

The Web server starts on `http://0.0.0.0:5000`.

---

## First-Time Configuration

1. Open your browser and navigate to:
   ```text
   http://<your-pi-ip>:5000/settings
   ```
2. Because the database is unconfigured, you will be redirected to the **Setup Wizard** (`/setup`).
3. Set your administrative username and password.
4. Log in at `/login` to access the Settings Dashboard where you can configure:
   - **Backlight Paths** for screen power control.
   - **MQTT Connection** settings.
   - **Motion Detection** threshold levels.
   - **Video Recording** folders.

---

## Running as a systemd Service

To run WakeOnPi automatically on startup as a background service:

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/wakeonpi.service
   ```

2. Paste the following configuration:
   ```ini
   [Unit]
   Description=WakeOnPi - Raspberry Pi Camera & Screen Service
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

3. Reload systemd, enable, and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable wakeonpi.service
   sudo systemctl start wakeonpi.service
   ```

4. Verify service status:
   ```bash
   sudo systemctl status wakeonpi.service
   ```

---

## Troubleshooting

### Camera Not Detected
- Verify the physical connection.
- Ensure the user running the service belongs to the video group:
  ```bash
  sudo usermod -a -G video pi
  ```

### Screen Control Failures
- Verify your backlight sysfs path exists: `ls /sys/class/backlight/`
- Ensure the user has write permissions to `/sys/class/backlight/.../bl_power` or similar control endpoints.
