@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo ==========================================
echo   智仓 · 库存管理后台 打包脚本
echo ==========================================
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo [提示] 未检测到 Node.js，跳过前端构建，使用 backend\static 中已有的产物。
  goto :backend
)

where pnpm >nul 2>nul
if errorlevel 1 (
  echo [提示] 未检测到 pnpm，跳过前端构建，使用 backend\static 中已有的产物。
  echo        如需重新构建前端，请先执行：npm install -g pnpm
  goto :backend
)

echo [1/5] 构建 PC 前端 ...
pushd frontend-pc
if not exist node_modules (
  call pnpm install
  if errorlevel 1 (
    echo [错误] PC 依赖安装失败，请检查网络或 pnpm 环境。
    popd & goto :error
  )
)
call pnpm build
if errorlevel 1 (
  echo [错误] PC 前端构建失败。
  popd & goto :error
)
popd
if not exist backend\static\pc mkdir backend\static\pc
xcopy /E /I /Y frontend-pc\dist\* backend\static\pc\ >nul

echo [2/5] 构建 H5 前端 ...
pushd frontend-h5
if not exist node_modules (
  call pnpm install
  if errorlevel 1 (
    echo [错误] H5 依赖安装失败，请检查网络或 pnpm 环境。
    popd & goto :error
  )
)
call pnpm build
if errorlevel 1 (
  echo [错误] H5 前端构建失败。
  popd & goto :error
)
popd
if not exist backend\static\m mkdir backend\static\m
xcopy /E /I /Y frontend-h5\dist\* backend\static\m\ >nul

:backend
echo [3/5] 检查 Python 依赖 ...
python -c "import flask, sqlalchemy, jwt, waitress" >nul 2>nul
if errorlevel 1 (
  python -m pip install -r requirements-dev.txt
  if errorlevel 1 (
    echo [错误] Python 依赖安装失败。
    goto :error
  )
)

echo [4/5] 打包 exe（目录模式，启动更快、更少杀软误报）...
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\work-dir build\app_dir.spec
if errorlevel 1 (
  echo [错误] PyInstaller 打包失败。
  goto :error
)

echo [5/5] 输出交付目录 ...
if exist "release\智仓管理后台" rmdir /S /Q "release\智仓管理后台"
mkdir "release\智仓管理后台"
xcopy /E /I /Y dist\SmartStock\* "release\智仓管理后台\" >nul
ren "release\智仓管理后台\SmartStock.exe" "智仓管理后台.exe"
copy /Y docs\使用说明.md "release\智仓管理后台\使用说明.md" >nul

echo.
echo 打包完成：release\智仓管理后台\智仓管理后台.exe
echo 双击该 exe 即可运行，首次运行会在同级目录创建 data 文件夹。
echo 如需单文件版，可执行：python -m PyInstaller build\app.spec
echo.
pause
exit /b 0

:error
echo.
echo 打包终止，请根据上方提示排查。
pause
exit /b 1
