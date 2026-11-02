@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在启动 智仓 · 库存管理后台 ...
python -c "import flask, sqlalchemy, jwt, waitress" >nul 2>nul
if errorlevel 1 (
  echo 首次运行，正在安装依赖 ...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 依赖安装失败，请检查 Python 与网络环境。
    pause
    exit /b 1
  )
)

python run.py
pause
