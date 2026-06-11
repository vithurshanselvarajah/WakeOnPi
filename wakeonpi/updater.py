import os
import sys
import logging
import threading
import urllib.request
import urllib.error
import json
from . import state

updater_instance = None

log = logging.getLogger("Updater")

def _get_updater_instance():
    global updater_instance
    if updater_instance is None:
        from .github_updater import GitHubReleaseUpdater
        updater_instance = GitHubReleaseUpdater()
    return updater_instance

def fetch_latest_version():
    url = "https://raw.githubusercontent.com/vithurshanselvarajah/WakeOnPi/main/pyproject.toml"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WakeOnPi-Updater"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("version") and "=" in line:
                    _, val = line.split("=", 1)
                    v = val.strip().strip('"').strip("'")
                    log.info(f"Fetched latest version {v} from raw pyproject.toml")
                    return v
    except Exception as e:
        log.warning(f"Failed to fetch version from raw pyproject.toml: {e}")
        api_url = "https://api.github.com/repos/vithurshanselvarajah/WakeOnPi/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "WakeOnPi-Updater"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                tag = data.get("tag_name", "")
                if tag.startswith("v"):
                    tag = tag[1:]
                if tag:
                    log.info(f"Fetched latest version {tag} from GitHub releases")
                    return tag
        except Exception as api_err:
            log.warning(f"Failed to fetch version from GitHub releases: {api_err}")
    return None

def check_for_updates(triggered_by: str = None):
    with state.update_lock:
        state.update_status = "checking"
        if triggered_by:
            state.update_initiated_by = triggered_by
    try:
        latest = fetch_latest_version()
        with state.update_lock:
            if latest:
                state.latest_version = latest
                state.update_status = "idle"
                return latest
            else:
                state.update_status = "failed"
                state.update_error = "Could not check latest version"
                state.update_initiated_by = None
    except Exception as e:
        with state.update_lock:
            state.update_status = "failed"
            state.update_error = str(e)
            state.update_initiated_by = None
    return None

def restart_process():
    log.info("Restarting WakeOnPi in-place...")
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        log.exception("In-place restart failed, exiting process.")
        sys.exit(1)

def _update_worker(triggered_by: str = None):
    with state.update_lock:
        if state.update_status == "installing":
            return
        state.update_status = "installing"
        state.update_error = None
        if triggered_by:
            state.update_initiated_by = triggered_by
    try:
        updater = _get_updater_instance()
        tag = updater.fetch_latest_release(triggered_by=triggered_by)
        log.info(f"Latest release tag resolved to {tag}")
        updater.install_release(tag)
        log.info("Update installed successfully. Restarting service...")
        with state.update_lock:
            state.update_status = "idle"
            state.update_initiated_by = None
        restart_process()
    except Exception as e:
        log.exception("Update installation failed")
        with state.update_lock:
            state.update_status = "failed"
            state.update_error = str(e)
            state.update_initiated_by = None

def trigger_update(triggered_by: str = None):
    threading.Thread(target=_update_worker, args=(triggered_by,), daemon=True).start()
