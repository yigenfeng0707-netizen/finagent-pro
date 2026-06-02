@echo off
chcp 65001 >nul
echo ==========================================
echo FinAgent Pro - 启动脚本
echo ==========================================
echo.

cd %~dp0\..

REM 检查虚拟环境
if not exist venv\Scripts\activate.bat (
    echo [错误] 虚拟环境不存在，请先运行 scripts\setup.bat
    exit /b 1
)

echo [1/3] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [2/3] 启动后端服务...
start "FinAgent Pro - 后端" cmd /k "cd backend && python main.py"

echo [3/3] 启动前端服务...
timeout /t 3 >nul
start "FinAgent Pro - 前端" cmd /k "cd frontend && npm start"

echo.
echo ==========================================
echo 服务启动中...
echo ==========================================
echo.
echo 后端API: http://localhost:8000
echo 前端界面: http://localhost:3000
echo API文档: http://localhost:8000/docs
echo.
echo 按任意键关闭所有服务...
pause >nul

taskkill /FI "WINDOWTITLE eq FinAgent Pro - 后端" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FinAgent Pro - 前端" /F >nul 2>&1

echo 服务已关闭
