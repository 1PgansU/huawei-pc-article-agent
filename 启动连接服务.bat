@echo off
chcp 65001 >nul
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Node.js。请先安装 https://nodejs.org/ 后再运行本脚本。
  pause
  exit /b 1
)

if not exist "connect-server.js" (
  echo [错误] 未找到 connect-server.js，请确认本脚本在「华为赛题」项目根目录。
  pause
  exit /b 1
)

if not exist "ima-skill\ima_api.cjs" (
  echo [提示] 未找到 ima-skill\ima_api.cjs，云端连接将不可用，仍可使用本地知识库。
)

echo.
echo ========================================
echo  华为PC营销软文 · 连接服务
echo  浏览器打开: http://127.0.0.1:8787/
echo  凭证: 项目根目录 .env 中的 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY
echo        或环境变量 IMA_CLIENT_ID / IMA_API_KEY，或 %%USERPROFILE%%\.config\ima\
echo  本地库默认: Desktop\华为赛题\华为PC知识库
echo  按 Ctrl+C 可停止
echo ========================================
echo.

start "" "http://127.0.0.1:8787/"
node connect-server.js
pause
