@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

echo 正在启动 智仓 · 库存管理后台 ...
"%PY%" -c "import flask, sqlalchemy, jwt, waitress" >nul 2>nul
if errorlevel 1 (
  echo 首次运行，正在安装依赖 ...
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 直连 PyPI 失败，改用国内镜像重试 ...
    "%PY%" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
  )
  if errorlevel 1 (
    echo 依赖安装失败，请检查 Python 与网络环境。
    pause
    exit /b 1
  )
)

"%PY%" run.py
pause
