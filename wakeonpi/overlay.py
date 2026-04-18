import time
import threading
import logging
from datetime import datetime
from . import state

log = logging.getLogger("Overlay")

_notification_message = None
_notification_persistent = True
_overlay_lock = threading.Lock()
_display_thread = None
_stop_event = threading.Event()


def set_notification(message, persistent=True):
    global _notification_message, _notification_persistent
    with _overlay_lock:
        _notification_message = message
        _notification_persistent = persistent
        log.info(f"Display notification set: {message}")


def clear_notification():
    global _notification_message
    with _overlay_lock:
        _notification_message = None
        log.info("Display notification cleared")


def get_notification():
    with _overlay_lock:
        return _notification_message


def get_current_time():
    return datetime.now().strftime("%H:%M")


def get_display_info():
    with _overlay_lock:
        return {
            "time": get_current_time(),
            "notification": _notification_message,
            "has_notification": _notification_message is not None
        }


def _update_browser_overlay():
    try:
        from . import browser
        info = get_display_info()
        js_code = f'''
            (function() {{
                let overlay = document.getElementById('wakeonpi-overlay');
                if (!overlay) {{
                    overlay = document.createElement('div');
                    overlay.id = 'wakeonpi-overlay';
                    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:8px 16px;background:rgba(0,0,0,0.7);color:white;font-family:sans-serif;z-index:999999;display:flex;justify-content:space-between;align-items:center;font-size:18px;';
                    document.body.appendChild(overlay);
                }}
                let timeStr = '{info["time"]}';
                let notif = {repr(info["notification"]) if info["notification"] else 'null'};
                overlay.innerHTML = '<span style="font-weight:bold;">' + timeStr + '</span>' + 
                    (notif ? '<span style="background:#f59e0b;padding:4px 12px;border-radius:4px;margin-left:16px;">' + notif + '</span>' : '');
            }})();
        '''
        browser._get_controller()._run_on_worker(
            lambda: browser._get_controller()._execute_cdp_js(js_code),
            wait=False
        )
    except Exception:
        pass


def start_overlay_service():
    global _display_thread
    if _display_thread and _display_thread.is_alive():
        return
    _stop_event.clear()
    _display_thread = threading.Thread(target=_overlay_loop, daemon=True)
    _display_thread.start()
    log.info("Display overlay service started")


def stop_overlay_service():
    _stop_event.set()
    if _display_thread:
        _display_thread.join(timeout=2)


def _overlay_loop():
    while not _stop_event.is_set():
        try:
            _update_browser_overlay()
        except Exception:
            pass
        _stop_event.wait(30)

