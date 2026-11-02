"""应用配置：路径、端口、安全参数。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ID = "smart-stock"
APP_NAME = "智仓"
APP_SUBTITLE = "库存管理后台"
VERSION = "1.0.0"

DEFAULT_PORT = int(os.environ.get("SMARTSTOCK_PORT", "8000"))
HOST = os.environ.get("SMARTSTOCK_HOST", "0.0.0.0")
TOKEN_HOURS = int(os.environ.get("SMARTSTOCK_TOKEN_HOURS", "12"))
LOW_STOCK_DEFAULT = int(os.environ.get("SMARTSTOCK_LOW_STOCK", "5"))
MAX_LOGIN_FAILURES = 5
LOCK_MINUTES = 10
PAGE_SIZE_DEFAULT = 10
PAGE_SIZE_MAX = 100


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """只读资源根目录（前端产物、模板）。打包后位于临时解压目录。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def app_root() -> Path:
    """可写根目录：exe 所在目录；开发时为项目根目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    override = os.environ.get("SMARTSTOCK_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    base = app_root() / "data"
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return base
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SmartStock"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = data_dir()
DB_PATH = DATA_DIR / "app.db"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"
PORT_FILE = DATA_DIR / "port.txt"
SECRET_FILE = DATA_DIR / "secret.key"
LOCK_FILE = DATA_DIR / "app.lock"
