import threading
import time
import os
from pathlib import Path
import cv2
import logging
from . import camera, state, config

log = logging.getLogger('Recorder')

class Recorder:
    def __init__(self):
        self._thread = None
        self._stop = threading.Event()
        self._file = None
        self._lock = threading.Lock()

    def _make_filepath(self, root: str):
        base = Path(root)
        base.mkdir(parents=True, exist_ok=True)
        day = time.strftime('%Y-%m-%d')
        ddir = base / day
        ddir.mkdir(parents=True, exist_ok=True)
        fname = time.strftime('%Y%m%d-%H%M%S') + '.mp4'
        return str(ddir / fname)

    def _record_loop(self, path):
        try:
            camera.switch_to_full_mode()
            time.sleep(0.5)
            picam2 = camera.picam2
            frame = picam2.capture_array('main')
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(path, fourcc, 10.0, (w, h))
            if not out.isOpened():
                log.error(f'Failed to open VideoWriter for {path}')
                return
            while not self._stop.is_set():
                frame = picam2.capture_array('main')
                try:
                    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                except Exception:
                    bgr = frame
                out.write(bgr)
                time.sleep(0.1)
            out.release()
        except Exception:
            log.exception('Recording loop failed')
        finally:
            try:
                camera.switch_to_lores_mode_if_needed()
            except Exception:
                pass

    def start(self, root=None):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False, 'Already recording'
            root = root or config.RECORDINGS_ROOT
            try:
                path = self._make_filepath(root)
            except Exception as e:
                return False, f'Failed to create recording path: {e}'
            self._stop.clear()
            t = threading.Thread(target=self._record_loop, args=(path,), daemon=True)
            self._thread = t
            t.start()
            self._file = path
            return True, path

    def stop(self):
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return False, 'Not recording'
            self._stop.set()
            self._thread.join(timeout=5)
            self._thread = None
            f = self._file
            self._file = None
            return True, f

    def is_recording(self):
        return self._thread is not None and self._thread.is_alive()

    def check_root_writable(self, root=None):
        r = root or config.RECORDINGS_ROOT
        try:
            p = Path(r)
            p.mkdir(parents=True, exist_ok=True)
            test = p / '._writable_test'
            with test.open('w') as f:
                f.write('ok')
            test.unlink()
            return True, 'OK'
        except Exception as e:
            return False, str(e)

_recorder = Recorder()

def start_recording(root=None):
    return _recorder.start(root)

def stop_recording():
    return _recorder.stop()

def is_recording():
    return _recorder.is_recording()

def check_root_writable(root=None):
    return _recorder.check_root_writable(root)

def get_current_file():
    return getattr(_recorder, '_file', None)
