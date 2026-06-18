import threading
import time
import collections
import socket
import json
import logging
from pathlib import Path

log = logging.getLogger("State")

motion_event = False
last_motion_time = 0
current_frame = None
frame_lock = threading.Lock()
clients_connected = 0
clients_lock = threading.Lock()
main_stream_active = False
main_stream_lock = threading.Lock()
display_on = True
ignore_motion_until = 0
motion_prev_frame_stale = False
manual_display_override = False
stream_url = None
browser_url = None
browser_override_url = None
temp_backlight_test = None
temp_recordings_test = None

update_status = "idle"
latest_version = None
update_error = None
update_lock = threading.Lock()

installed_versions: list = []
current_version: str = ""
update_initiated_by: str | None = None
brightness_level = 100
brightness_lock = threading.Lock()
db_load_error = None

ws_clients = set()
ws_clients_lock = threading.Lock()

system_stats = {
    "cpu_temp": 0,
    "cpu_usage": 0,
    "memory_percent": 0,
    "uptime": 0,
    "storage_free_gb": 0,
    "storage_total_gb": 0,
    "storage_percent": 0,
}
system_stats_lock = threading.Lock()

log_buffer = collections.deque(maxlen=500)
log_buffer_lock = threading.Lock()

_start_time = time.time()
_system_ip = None


def get_uptime():
    return int(time.time() - _start_time)


def get_system_ip():
    global _system_ip
    if _system_ip:
        return _system_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        _system_ip = s.getsockname()[0]
        s.close()
    except Exception:
        _system_ip = "127.0.0.1"
    return _system_ip


def add_log(level, name, message):
    with log_buffer_lock:
        log_buffer.append(
            {"timestamp": time.time(), "level": level, "name": name, "message": message}
        )


def get_logs(level_filter=None, limit=100):
    with log_buffer_lock:
        logs = list(log_buffer)
    if level_filter:
        level_filter = level_filter.upper()
        logs = [log for log in logs if log["level"] == level_filter]
    return logs[-limit:]

MANIFEST_PATH = Path(__file__).parent / "updates" / "manifest.json"

def load_manifest():
    global installed_versions, current_version
    if not MANIFEST_PATH.exists():
        return
    try:
        data = json.loads(MANIFEST_PATH.read_text())
        installed_versions = [item["tag"] for item in data.get("installed", [])]
        current_version = data.get("current", "")
    except Exception as e:
        log.exception(f"Failed to load manifest: {e}")

def save_manifest():
    try:
        manifest = {
            "installed": [{"tag": v, "path": f"updates/{v}", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} for v in installed_versions],
            "current": current_version,
            "last_error": None,
        }
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    except Exception as e:
        log.exception(f"Failed to save manifest: {e}")

load_manifest()

