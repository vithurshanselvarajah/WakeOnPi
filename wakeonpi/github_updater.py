import json
import urllib.request
import urllib.error
import logging
import time
import hashlib
import zipfile
import shutil
from pathlib import Path
from typing import Callable, List, Optional

from . import state

log = logging.getLogger("GitHubReleaseUpdater")
GITHUB_API = "https://api.github.com"
REPO_OWNER = "vithurshanselvarajah"
REPO_NAME = "WakeOnPi"

class GitHubReleaseUpdater:
    def __init__(self):
        self.updates_dir = Path(__file__).parent / "updates"
        self.updates_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.updates_dir / "manifest.json"
        self._load_manifest()

    def _load_manifest(self):
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text())
                state.installed_versions = [item["tag"] for item in data.get("installed", [])]
                state.current_version = data.get("current", "")
                state.update_initiated_by = None
            except Exception as e:
                log.exception(f"Failed to load manifest: {e}")
        else:
            state.installed_versions = []
            state.current_version = ""
            self._save_manifest()

    def _save_manifest(self):
        try:
            manifest = {
                "installed": [
                    {
                        "tag": v,
                        "path": f"updates/{v}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                    for v in state.installed_versions
                ],
                "current": state.current_version,
                "last_error": None,
            }
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            self.manifest_path.write_text(json.dumps(manifest, indent=2))
        except Exception as e:
            log.exception(f"Failed to save manifest: {e}")

    def _github_api(self, endpoint: str) -> dict:
        url = f"{GITHUB_API}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "WakeOnPi-Updater"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def fetch_latest_release(self, triggered_by: Optional[str] = None) -> str:
        data = self._github_api(f"/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest")
        tag = data.get("tag_name", "")
        if tag.startswith("v"):
            tag = tag[1:]
        if not tag:
            raise RuntimeError("Latest release tag not found")
        with state.update_lock:
            state.latest_version = tag
            state.update_initiated_by = triggered_by
        return tag

    def _asset_url(self, assets: List[dict], suffix: str) -> str:
        for a in assets:
            if a.get("name", "").endswith(suffix):
                return a.get("browser_download_url")
        raise RuntimeError(f"Asset ending with {suffix} not found")

    def download_release(self, tag: str) -> Path:
        release_data = self._github_api(f"/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/v{tag}")
        assets = release_data.get("assets", [])
        zip_url = self._asset_url(assets, f"wakeonpi-{tag}.zip")
        checksum_url = self._asset_url(assets, f"wakeonpi-{tag}.zip.sha256")
        tmp_dir = self.updates_dir / f"tmp_{tag}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = tmp_dir / f"wakeonpi-{tag}.zip"
        checksum_path = tmp_dir / f"wakeonpi-{tag}.zip.sha256"
        urllib.request.urlretrieve(zip_url, zip_path)
        urllib.request.urlretrieve(checksum_url, checksum_path)
        return zip_path

    def verify_checksum(self, zip_path: Path) -> None:
        checksum_file = zip_path.with_name(zip_path.name + ".sha256")
        if not checksum_file.exists():
            raise RuntimeError("Checksum file missing for downloaded release")
        expected = checksum_file.read_text().strip().split()[0]
        sha256 = hashlib.sha256()
        with zip_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        actual = sha256.hexdigest()
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch: expected {expected}, got {actual}")
        log.info("Checksum verification passed")

    def install_release(self, tag: str) -> None:
        zip_path = self.download_release(tag)
        self.verify_checksum(zip_path)
        target_dir = self.updates_dir / tag
        if target_dir.exists():
            shutil.rmtree(target_dir)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)
        tmp_dir = zip_path.parent
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        state.current_version = tag
        if tag not in state.installed_versions:
            state.installed_versions.append(tag)
        self._save_manifest()
        self.prune_versions(except_tag=tag)

    def rollback(self, tag: str, restart_callback: Optional[Callable[[], None]] = None) -> None:
        if tag not in state.installed_versions:
            raise RuntimeError(f"Tag {tag} is not installed")
        state.current_version = tag
        self._save_manifest()
        if restart_callback is not None:
            restart_callback()

    def prune_versions(self, except_tag: Optional[str] = None) -> None:
        for v in list(state.installed_versions):
            if v == except_tag:
                continue
            path = self.updates_dir / v
            if path.exists():
                shutil.rmtree(path)
            state.installed_versions.remove(v)
        self._save_manifest()

    def fetch_release_notes(self, tag: str) -> str:
        try:
            data = self._github_api(f"/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/v{tag}")
            return data.get("body", "")
        except Exception:
            return ""
