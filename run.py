"""开发/生产启动入口：python run.py"""
from __future__ import annotations

import sys

from backend.app import create_app
from backend.server import serve, setup_logging, show_fatal_error


def main() -> None:
    setup_logging()
    serve(create_app())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        show_fatal_error(f"程序启动失败：{exc}\n详情见 data/logs/app.log")
        sys.exit(1)
