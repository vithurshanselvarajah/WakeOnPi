import threading
import os
import shutil
import time
import logging
import queue
import subprocess


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
        self._paused = False

    def _find_executable(self):
        for p in _DEFAULT_CHROMIUM_PATHS:
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p
        return None

    def _worker(self):
        try:
            self._started = True
            self._paused = False
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
            self._paused = False
            log.info("Browser worker exited")

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
                    mqtt.publish_browser_current_page(url)
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
            "--start-fullscreen",
            "--window-size=1280,720",
            "--remote-debugging-port=9222",
            url,
        ]

        try:
            self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            log.exception("Failed to start chromium process")
            self._proc = None
            raise RuntimeError("Failed to start chromium process")
        try:
            import wakeonpi.mqtt as mqtt
            mqtt.publish_browser_current_page(url)
        except Exception:
            log.exception("Failed to publish browser stream URL after chromium start")

    def refresh(self):
        def _do():
            if not self.current_url:
                return
            self._restart_process(self.current_url)

        with _lock:
            if not self._started:
                return
            self._run_on_worker(_do)

    def pause(self):
        def _do():
            if self._paused:
                return
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=5)
                except Exception:
                    log.exception("Failed to terminate chromium on pause; killing")
                    try:
                        self._proc.kill()
                    except Exception:
                        log.exception("Failed to kill chromium process on pause")
            self._proc = None
            self._paused = True

        with _lock:
            if not self._started:
                return
            self._run_on_worker(_do)

    def resume(self, refresh_page=True):
        def _do():
            if not self._paused:
                return
            target = self.current_url or self._one_shot_url or "about:blank"
            use_url = self.current_url if (self.current_url and refresh_page) else target
            self._restart_process(use_url)
            self._paused = False

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


def pause():
    _get_controller().pause()


def resume(refresh_page=True):
    _get_controller().resume(refresh_page=refresh_page)


def stop():
    _get_controller().stop()


def get_current_url():
    try:
        return _get_controller().current_url
    except Exception:
        return None