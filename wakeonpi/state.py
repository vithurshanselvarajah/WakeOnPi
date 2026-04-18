import threading
import time
import collections
import socket

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
manual_display_override = False
stream_url = None
browser_url = None
browser_override_url = None
temp_backlight_test = None
temp_recordings_test = None

overlay_message = None
overlay_expires = 0
overlay_lock = threading.Lock()

brightness_level = 100
brightness_lock = threading.Lock()

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
        log_buffer.append({
            "timestamp": time.time(),
            "level": level,
            "name": name,
            "message": message
        })

def get_logs(level_filter=None, limit=100):
    with log_buffer_lock:
        logs = list(log_buffer)
    if level_filter:
        level_filter = level_filter.upper()
        logs = [l for l in logs if l["level"] == level_filter]
    return logs[-limit:]