@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting Huawei PC marketing agent on http://127.0.0.1:8765
if exist "D:\anaconda3\python.exe" (
  "D:\anaconda3\python.exe" -c "import yaml" >nul 2>&1 && (
    "D:\anaconda3\python.exe" api_server.py
    goto :end
  )
)
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ and PyYAML: pip install -r requirements.txt
  pause
  goto :end
)
python -c "import yaml" >nul 2>&1
if errorlevel 1 (
  echo Installing PyYAML ...
  python -m pip install -r requirements.txt
)
python api_server.py
:end
pause
