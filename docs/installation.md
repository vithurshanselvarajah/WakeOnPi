# Installation Guide

## Prerequisites

- Raspberry Pi (3, 4, or 5 recommended) running Raspberry Pi OS.
- Python 3.11 or later.
- Camera module connected and enabled.

---

## System and Python Dependencies

Install the required system and Python packages via `apt`:

```bash
sudo apt-get update
sudo apt-get install -y \
    git \
    python3-flask \
    python3-paho-mqtt \
    python3-opencv \
    python3-picamera2 \
    python3-pip
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

2. **Install Remaining Python Dependencies**:

   You can choose to install within a virtual environment or system-wide:

   ### Option A: Using a Virtual Environment (Recommended)
   Create a virtual environment that can access the `apt`-installed system packages:
   ```bash
   python3 -m venv venv --system-site-packages
   source venv/bin/activate
   pip install flask-sock
   ```

   ### Option B: System-wide Installation (without Virtual Environment)
   On modern Raspberry Pi OS releases (Bookworm+), installing globally via `pip` requires the `--break-system-packages` flag for packages not in apt:
   ```bash
   sudo pip3 install flask-sock --break-system-packages
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
   http://<your-pi-ip>:5000/
   ```
2. On first connection, you will be automatically redirected to the **Setup Wizard** (`/setup`).
3. Create your administrative username and password (you will be asked to confirm the password).
4. After submitting, you are automatically logged in and taken to the Settings Dashboard.
5. Configure your system:
   - **Backlight Paths** for screen power control.
   - **MQTT Connection** settings.
   - **Motion Detection** threshold levels.
   - **Video Recording** folders.

> **Note**: Until you complete the setup wizard, all URLs (including `/login` and `/settings`) redirect to `/setup`. The login page only becomes available after an admin account has been created.

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
Description=WakeOnPi - motion-aware camera stream and display controller
After=network.target

[Service]
WorkingDirectory=/home/<username>/WakeOnPi

ExecStart=/home/<username>/WakeOnPi/venv/bin/python /home/<username>/WakeOnPi/run.py

Environment=DISPLAY=:0

Restart=always
RestartSec=5

User=<username>

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
