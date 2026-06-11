import sqlite3
import hashlib
import secrets
import logging
import os
from pathlib import Path

log = logging.getLogger("Database")
DB_FILE = Path(__file__).parent / "wakeonpi.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        log.exception("Database connection failed")
        from . import state
        state.db_load_error = str(e)
        raise

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            conn.commit()
        from . import state
        state.db_load_error = None
    except Exception as e:
        log.exception("Failed to initialize database")
        from . import state
        state.db_load_error = str(e)

def check_db_health():
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1 FROM settings LIMIT 1").fetchone()
        from . import state
        state.db_load_error = None
    except Exception as e:
        log.exception("Database health check failed")
        from . import state
        state.db_load_error = str(e)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 100000
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{salt.hex()}${iterations}${pwd_hash.hex()}"

def verify_password(password: str, hashed_value: str) -> bool:
    try:
        if not hashed_value or "$" not in hashed_value:
            return False
        parts = hashed_value.split("$")
        if len(parts) != 3:
            return False
        salt = bytes.fromhex(parts[0])
        iterations = int(parts[1])
        correct_hash = bytes.fromhex(parts[2])
        test_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(correct_hash, test_hash)
    except Exception:
        log.exception("Password verification failed")
        return False

def get_setting(key: str, default=None) -> str:
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row:
                return row["value"]
    except Exception as e:
        log.exception(f"Failed to read setting: {key}")
        from . import state
        state.db_load_error = str(e)
    return default

def set_setting(key: str, value: str):
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value) if value is not None else None),
            )
            conn.commit()
        from . import state
        state.db_load_error = None
    except Exception as e:
        log.exception(f"Failed to write setting: {key}")
        from . import state
        state.db_load_error = str(e)

def get_all_settings() -> dict:
    settings = {}
    try:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            for row in rows:
                settings[row["key"]] = row["value"]
        from . import state
        state.db_load_error = None
    except Exception as e:
        log.exception("Failed to fetch all settings")
        from . import state
        state.db_load_error = str(e)
    return settings

def reset_db():
    try:
        if DB_FILE.exists():
            os.remove(DB_FILE)
        init_db()
        from . import state
        state.db_load_error = None
    except Exception as e:
        log.exception("Failed to reset database")
        from . import state
        state.db_load_error = str(e)

if not DB_FILE.exists():
    init_db()
check_db_health()
