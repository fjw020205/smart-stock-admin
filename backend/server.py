"""启动器：单实例、端口探测、日志、自动打开浏览器、waitress 服务。"""
from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler

from waitress import serve as waitress_serve

from .config import APP_NAME, APP_SUBTITLE, DEFAULT_PORT, HOST, LOG_FILE, PORT_FILE, VERSION
from .db import init_db

logger = logging.getLogger("smartstock")
_lock_handle = None


def setup_logging() -> None:
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if sys.stdout and sys.stdout.isatty():
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(formatter)
        logger.addHandler(stream)


def acquire_instance_lock():
    """Windows 文件锁：防止双击多次启动。"""
    global _lock_handle
    try:
        handle = open(PORT_FILE.parent / "app.lock", "a+")
        handle.seek(0)
        handle.write("1")
        handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_handle = handle
        return handle
    except OSError:
        return None


def read_port() -> int:
    try:
        return int(PORT_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return DEFAULT_PORT


def pick_port(preferred: int) -> int:
    for port in range(preferred, preferred + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # 不要设置 SO_REUSEADDR：Windows 下它会把已被占用的端口误判为空闲
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    return preferred


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def open_browser_later(url: str) -> None:
    if os.environ.get("SMARTSTOCK_NO_BROWSER") == "1":
        return

    def _open():
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:  # pragma: no cover - 浏览器异常不影响服务
            pass

    threading.Thread(target=_open, daemon=True).start()


def banner(url: str) -> None:
    ip = lan_ip()
    lines = [
        "",
        f"  {APP_NAME} · {APP_SUBTITLE}  v{VERSION}",
        f"  本机访问 : {url}",
        f"  手机访问 : http://{ip}:{url.rsplit(':', 1)[-1]}/m/   (需同一局域网)",
        "  关闭本窗口即停止服务，数据保存在 data/app.db",
        "",
    ]
    text = "\n".join(lines)
    if sys.stdout:
        print(text)
    logger.info(text.replace("\n", " | "))


def serve(app) -> None:
    setup_logging()

    if acquire_instance_lock() is None:
        port = read_port()
        logger.info("检测到程序已在运行，直接打开浏览器")
        webbrowser.open(f"http://127.0.0.1:{port}/")
        return

    init_db()
    port = pick_port(DEFAULT_PORT)
    PORT_FILE.write_text(str(port), encoding="utf-8")
    url = f"http://127.0.0.1:{port}"

    banner(url)
    open_browser_later(url)

    try:
        waitress_serve(app, host=HOST, port=port, threads=8, channel_timeout=120)
    except KeyboardInterrupt:
        logger.info("服务已停止")
    finally:
        global _lock_handle
        if _lock_handle is not None:
            try:
                _lock_handle.close()
            except OSError:
                pass
            _lock_handle = None


def show_fatal_error(message: str) -> None:
    logger.exception(message)
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, f"{APP_NAME} 启动失败", 0x10)
        except Exception:
            pass
