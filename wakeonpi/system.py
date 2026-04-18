import threading
import time
import os
import logging
from pathlib import Path
from . import state, config

log = logging.getLogger("System")

_stats_thread = None
_stop_event = threading.Event()


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(int(f.read().strip()) / 1000, 1)
    except Exception:
        return 0


def get_cpu_usage():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = line.split()
        idle = int(parts[4])
        total = sum(int(p) for p in parts[1:])
        if not hasattr(get_cpu_usage, "_prev"):
            get_cpu_usage._prev = (idle, total)
            return 0
        prev_idle, prev_total = get_cpu_usage._prev
        get_cpu_usage._prev = (idle, total)
        diff_idle = idle - prev_idle
        diff_total = total - prev_total
        if diff_total == 0:
            return 0
        return round((1 - diff_idle / diff_total) * 100, 1)
    except Exception:
        return 0


def get_memory_usage():
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                mem[parts[0].rstrip(":")] = int(parts[1])
        total = mem.get("MemTotal", 1)
        available = mem.get("MemAvailable", 0)
        used = total - available
        return round((used / total) * 100, 1)
    except Exception:
        return 0


def get_storage_info(path=None):
    try:
        check_path = path or config.RECORDINGS_ROOT or "/"
        p = Path(check_path)
        if not p.exists():
            p = Path("/")
        st = os.statvfs(str(p))
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        total_gb = round(total / (1024 ** 3), 2)
        free_gb = round(free / (1024 ** 3), 2)
        used_percent = round(((total - free) / total) * 100, 1) if total > 0 else 0
        return {
            "total_gb": total_gb,
            "free_gb": free_gb,
            "used_percent": used_percent
        }
    except Exception:
        return {"total_gb": 0, "free_gb": 0, "used_percent": 0}


def _update_stats():
    while not _stop_event.is_set():
        try:
            storage = get_storage_info()
            with state.system_stats_lock:
                state.system_stats["cpu_temp"] = get_cpu_temp()
                state.system_stats["cpu_usage"] = get_cpu_usage()
                state.system_stats["memory_percent"] = get_memory_usage()
                state.system_stats["uptime"] = state.get_uptime()
                state.system_stats["storage_free_gb"] = storage["free_gb"]
                state.system_stats["storage_total_gb"] = storage["total_gb"]
                state.system_stats["storage_percent"] = storage["used_percent"]
        except Exception:
            log.exception("Failed to update system stats")
        _stop_event.wait(5)


def start():
    global _stats_thread
    if _stats_thread and _stats_thread.is_alive():
        return
    _stop_event.clear()
    _stats_thread = threading.Thread(target=_update_stats, daemon=True)
    _stats_thread.start()
    log.info("System stats thread started")


def stop():
    _stop_event.set()
    if _stats_thread:
        _stats_thread.join(timeout=2)


def get_stats():
    with state.system_stats_lock:
        return state.system_stats.copy()


def get_health():
    stats = get_stats()
    storage = get_storage_info()
    return {
        "status": "healthy",
        "uptime": stats["uptime"],
        "cpu_temp": stats["cpu_temp"],
        "cpu_usage": stats["cpu_usage"],
        "memory_percent": stats["memory_percent"],
        "storage": storage,
        "camera_active": state.main_stream_active,
        "clients_connected": state.clients_connected,
        "motion_detected": state.motion_event,
        "display_on": state.display_on,
        "brightness": state.brightness_level,
    }
