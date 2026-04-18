import json
import logging
import subprocess
import threading
import urllib.request
import urllib.error
from pathlib import Path
from packaging import version as pkg_version

from . import config

log = logging.getLogger("Updater")

GITHUB_API_URL = "https://api.github.com/repos/vithurshanselvarajah/WakeOnPi/releases/latest"
GITHUB_RELEASES_URL = "https://api.github.com/repos/vithurshanselvarajah/WakeOnPi/releases"
PROJECT_ROOT = Path(__file__).parent.parent

_update_info = {
    "available": False,
    "current_version": None,
    "latest_version": None,
    "changelog": None,
    "breaking": False,
    "new_packages": [],
    "last_check": None,
    "checking": False,
    "updating": False,
    "update_error": None,
}
_lock = threading.Lock()


def get_current_version():
    try:
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        if pyproject_path.exists():
            with pyproject_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("version") and "=" in line:
                        _, val = line.split("=", 1)
                        return val.strip().strip('"').strip("'")
    except Exception:
        log.exception("Failed to read version from pyproject.toml")
    return "0.0.0"


def _parse_requirements(content):
    packages = set()
    for line in content.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].split("!=")[0].strip()
            if pkg:
                packages.add(pkg.lower())
    return packages


def _get_local_requirements():
    try:
        req_path = PROJECT_ROOT / "requirements.txt"
        if req_path.exists():
            return _parse_requirements(req_path.read_text())
    except Exception:
        log.exception("Failed to read local requirements.txt")
    return set()


def _fetch_remote_requirements(tag):
    try:
        url = f"https://raw.githubusercontent.com/vithurshanselvarajah/WakeOnPi/{tag}/requirements.txt"
        req = urllib.request.urlopen(url, timeout=10)
        return _parse_requirements(req.read().decode())
    except Exception:
        log.exception(f"Failed to fetch remote requirements for {tag}")
    return set()


def _detect_breaking_changes(remote_tag):
    local_pkgs = _get_local_requirements()
    remote_pkgs = _fetch_remote_requirements(remote_tag)
    new_packages = remote_pkgs - local_pkgs
    return list(new_packages) if new_packages else []


def check_for_updates():
    global _update_info
    
    with _lock:
        if _update_info["checking"]:
            return _update_info.copy()
        _update_info["checking"] = True
        _update_info["update_error"] = None
    
    try:
        current = get_current_version()
        
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "WakeOnPi"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        
        latest_tag = data.get("tag_name", "v0.0.0")
        latest = latest_tag.lstrip("v")
        changelog = data.get("body", "No changelog available.")
        
        is_newer = pkg_version.parse(latest) > pkg_version.parse(current)
        
        new_packages = []
        if is_newer:
            new_packages = _detect_breaking_changes(latest_tag)
        
        with _lock:
            _update_info = {
                "available": is_newer,
                "current_version": current,
                "latest_version": latest,
                "changelog": changelog,
                "breaking": len(new_packages) > 0,
                "new_packages": new_packages,
                "last_check": __import__("time").time(),
                "checking": False,
                "updating": False,
                "update_error": None,
            }
        
        log.info(f"Update check: current={current}, latest={latest}, available={is_newer}, breaking={len(new_packages) > 0}")
        
    except urllib.error.URLError as e:
        log.error(f"Network error checking for updates: {e}")
        with _lock:
            _update_info["checking"] = False
            _update_info["update_error"] = f"Network error: {e}"
    except Exception as e:
        log.exception("Failed to check for updates")
        with _lock:
            _update_info["checking"] = False
            _update_info["update_error"] = str(e)
    
    with _lock:
        return _update_info.copy()


def get_update_info():
    with _lock:
        return _update_info.copy()


def _run_git_command(*args):
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    return result.stdout.strip()


def perform_update():
    global _update_info
    
    with _lock:
        if _update_info["updating"]:
            return False, "Update already in progress"
        if not _update_info["available"]:
            return False, "No update available"
        if _update_info["breaking"]:
            return False, f"Breaking changes detected. New packages required: {', '.join(_update_info['new_packages'])}. Please update manually."
        _update_info["updating"] = True
        _update_info["update_error"] = None
    
    try:
        log.info("Starting update process...")
        
        _run_git_command("fetch", "origin", "main")
        
        _run_git_command("stash", "push", "-m", "WakeOnPi auto-update stash")
        
        try:
            _run_git_command("checkout", "main")
            _run_git_command("pull", "origin", "main")
        except Exception:
            _run_git_command("stash", "pop")
            raise
        
        try:
            _run_git_command("stash", "pop")
        except Exception:
            pass
        
        with _lock:
            _update_info["updating"] = False
            _update_info["available"] = False
            _update_info["current_version"] = _update_info["latest_version"]
        
        log.info("Update completed successfully. Restart required.")
        return True, "Update completed. Please restart the service."
        
    except subprocess.TimeoutExpired:
        log.error("Update timed out")
        with _lock:
            _update_info["updating"] = False
            _update_info["update_error"] = "Update timed out"
        return False, "Update timed out"
    except Exception as e:
        log.exception("Update failed")
        with _lock:
            _update_info["updating"] = False
            _update_info["update_error"] = str(e)
        return False, f"Update failed: {e}"


def check_for_updates_async():
    thread = threading.Thread(target=check_for_updates, daemon=True)
    thread.start()


def perform_update_async(callback=None):
    def _do_update():
        success, message = perform_update()
        if callback:
            callback(success, message)
    
    thread = threading.Thread(target=_do_update, daemon=True)
    thread.start()
