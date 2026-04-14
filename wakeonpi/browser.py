import threading
import os
import shutil
import time
import logging
import queue
import subprocess
import json
try:
    import urllib.request
except ImportError:
    urllib = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

log = logging.getLogger("BrowserController")

_DEFAULT_CHROMIUM_PATHS = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium-browser-stable"
]
_USER_DATA_DIR = os.path.expanduser("~/.config/wakeonpi_browser")

_lock = threading.Lock()
_controller = None


class _BrowserController:
    def __init__(self):
        self._thread = None
        self._cmd_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._proc = None
        self.current_url = None
        self._one_shot_url = None
        self._started = False
        self._url_monitor_thread = None

    def _find_executable(self):
        for p in _DEFAULT_CHROMIUM_PATHS:
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p
        return None

    def _worker(self):
        try:
            self._started = True
            log.info("Browser worker ready (process-controlled)")
            self._ready_event.set()

            while not self._stop_event.is_set():
                try:
                    cmd, resp_q = self._cmd_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    result = cmd()
                    resp_q.put((True, result))
                except Exception as e:
                    log.exception("Exception while executing browser command in worker")
                    resp_q.put((False, e))

        except Exception:
            log.exception("Browser worker encountered an unexpected error")
            self._ready_event.set()
        finally:
            try:
                if self._proc:
                    try:
                        self._proc.terminate()
                        self._proc.wait(timeout=5)
                    except Exception:
                        log.exception("Error terminating chromium process during cleanup")
            except Exception:
                log.exception("Error during cleanup of chromium process")

            self._proc = None
            self._started = False
            log.info("Browser worker exited")

    def _get_browser_url_from_cdp(self):
        """Get the current URL from Chrome DevTools Protocol."""
        if urllib is None:
            return None
        try:
            req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
            data = json.loads(req.read().decode())
            for tab in data:
                if tab.get("type") == "page":
                    return tab.get("url")
        except Exception:
            pass
        return None

    def _url_monitor_loop(self):
        """Monitor browser URL changes via CDP and update state."""
        log.info("URL monitor thread started")
        while not self._stop_event.is_set():
            try:
                if self._proc and self._proc.poll() is None:
                    url = self._get_browser_url_from_cdp()
                    if url and not url.startswith("about:"):
                        # publish if the URL is different from last published URL in state
                        last_published = None
                        try:
                            from . import state as _state
                            last_published = getattr(_state, 'browser_url', None)
                        except Exception:
                            last_published = None

                        if url != last_published:
                            log.info(f"Browser navigated to: {url}")
                            self.current_url = url
                            try:
                                import wakeonpi.mqtt as mqtt
                                mqtt.publish_browser_url(url)
                            except Exception:
                                log.exception("Failed to publish browser URL after navigation")
            except Exception:
                log.exception("Error in URL monitor loop")
            time.sleep(2)
        log.info("URL monitor thread exited")

    def _start_url_monitor(self):
        """Start the URL monitoring thread if not already running."""
        if self._url_monitor_thread is None or not self._url_monitor_thread.is_alive():
            self._url_monitor_thread = threading.Thread(target=self._url_monitor_loop, daemon=True)
            self._url_monitor_thread.start()

    def start(self):
        with _lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._stop_event.clear()
            self._ready_event.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

        if not self._ready_event.wait(15):
            log.error("Timeout waiting for browser worker to start")
            raise RuntimeError("Timeout starting browser worker")

        if not self._started:
            raise RuntimeError("Browser worker failed to start")

    def ensure_started(self):
        if not self._started:
            self.start()

    def _run_on_worker(self, fn, wait=True):
        if threading.current_thread() is self._thread:
            return fn()

        resp_q = queue.Queue()
        self._cmd_queue.put((fn, resp_q))
        if not wait:
            return None
        ok, val = resp_q.get()
        if not ok:
            raise val
        return val

    def show_url(self, url, force=False, one_shot=False):
        def _do():
            if not url:
                log.error("show_url called with empty URL")
                return

            if one_shot:
                self._one_shot_url = url
            else:
                self.current_url = url

            try:
                self._restart_process(url)
                try:
                    import wakeonpi.mqtt as mqtt
                    mqtt.publish_browser_url(url)
                except Exception:
                    log.exception("Failed to publish browser stream URL after show_url")
            finally:
                self._one_shot_url = None

        with _lock:
            self.ensure_started()
            self._run_on_worker(_do)

    def _restart_process(self, url):
        try:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=5)
                except Exception:
                    log.exception("Failed to terminate existing chromium process; killing")
                    try:
                        self._proc.kill()
                    except Exception:
                        log.exception("Failed to kill chromium process")
        except Exception:
            log.exception("Error while stopping existing chromium process")

        exe = self._find_executable()
        if not exe:
            raise RuntimeError("Chromium executable not found")

        args = [
            exe,
            "--kiosk",
            "--no-first-run",
            "--disable-infobars",
            "--remote-debugging-port=9222",
            "--remote-debugging-address=127.0.0.1",
            url,
        ]

        try:
            self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.current_url = url
        except Exception:
            log.exception("Failed to start chromium process")
            self._proc = None
            raise RuntimeError("Failed to start chromium process")
        try:
            import wakeonpi.mqtt as mqtt
            mqtt.publish_browser_url(url)
        except Exception:
            log.exception("Failed to publish browser stream URL after chromium start")
        
        # Start URL monitor to track navigation
        self._start_url_monitor()

    def refresh(self):
        def _do():
            if not self.current_url:
                return
            self._restart_process(self.current_url)

        with _lock:
            if not self._started:
                return
            self._run_on_worker(_do)

def _get_controller():
    global _controller
    with _lock:
        if _controller is None:
            _controller = _BrowserController()
        return _controller


def start():
    _get_controller().start()


def show_url(url, force=False, one_shot=False):
    _get_controller().show_url(url, force=force, one_shot=one_shot)


def refresh():
    _get_controller().refresh()


def stop():
    _get_controller().stop()


def get_current_url():
    try:
        return _get_controller().current_url
    except Exception:
        return None