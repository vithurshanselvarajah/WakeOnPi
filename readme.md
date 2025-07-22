# PiWake

**PiWake** is a motion-activated streaming service for the Raspberry Pi 5, designed specifically for use with the official Raspberry Pi **Touch Display 2**. It provides a real-time camera feed over the network and automatically turns the display on when motion is detected — turning it off after a period of inactivity to save power and extend display lifespan.

---

## 🔧 Features

- 📷 Live MJPEG stream from the Pi Camera via browser
- 🎯 Motion detection using low-res YUV frames
- 🖥️ Automatically powers the **Touch Display 2** on/off via sysfs
- 🔐 Basic authentication to protect the stream
- 💡 Smart mode switching: low-res for idle, full-res for active streaming
- ⚙️ Optimized for Raspberry Pi 5 hardware
- 🚀 Ready to run as a systemd service with environment-based credentials

---

## 🛠️ Installation & Setup

### 1. Clone the Repo

```bash
git clone https://github.com/vithurshanselvarajah/WakeOnPi.git
cd WakeOnPi
```

### 2. Install Dependencies

Make sure you have the following installed on your Raspberry Pi 5:

```bash
sudo apt update
sudo apt install python3-flask python3-opencv python3-picamera2
```

### 3. Launch the application

```bash
sudo MOTION_USERNAME=your_username MOTION_PASSWORD=your_password python3 wakeonpi.py
```

---

## 📿 Running as a systemd Service

### 1. Create a systemd Unit File (example)

```ini
# /etc/systemd/system/piwake.service
[Unit]
Description=PiWake - Motion-Aware Camera Stream & Display Controller
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/WakeOnPi/wakeonpi.py
WorkingDirectory=/home/pi/WakeOnPi
Environment=MOTION_USERNAME=your_username
Environment=MOTION_PASSWORD=your_password
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable piwake
sudo systemctl start piwake
```

---

## 💻 Accessing the Stream

Open a browser and go to:

```
http://<raspberry-pi-ip>:5000/
```

You'll be prompted to log in with the credentials you set via environment variables.

---

## 📌 Display Compatibility

- ✔️ Optimized for the **official Raspberry Pi Touch Display 2**
- ✔️ Uses `/sys/class/backlight/11-0045/bl_power` for backlight control
- ❌ May not work as-is on HDMI or other non-standard displays

> You can test backlight control manually with:

```bash
echo 0 | sudo tee /sys/class/backlight/11-0045/bl_power  # Turn ON
echo 1 | sudo tee /sys/class/backlight/11-0045/bl_power  # Turn OFF
```

---

## 🧪 Development Notes

- Uses low-resolution YUV frames for efficient motion detection
- Captures high-res frames only when streaming
- Adjust `MOTION_THRESHOLD` and `INACTIVITY_TIMEOUT` in the code to fine-tune behavior

---

## 📜 License

**Non-Commercial License** — You are free to use, modify, and share this project for **non-commercial purposes only**. Commercial use is **not permitted** without explicit permission from the author.

Contact the author to request a commercial license or discuss usage rights.