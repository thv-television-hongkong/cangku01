@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
    goto checkenv
)
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 (
    echo 请先安装 Python 3.10 或更高版本，并在安装时勾选 Add Python to PATH。
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
python -m venv .venv
:checkenv
if not exist ".venv\Scripts\python.exe" goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo 启动后在浏览器打开 http://127.0.0.1:5000
echo 首次运行会在此窗口显示随机生成的管理员密码，请保存。
echo 按 Ctrl+C 停止服务器。
".venv\Scripts\python.exe" -u app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo 启动未完成，请查看上方错误，并参阅 README.md 的常见问题。
pause
exit /b 1
