@echo off
chcp 65001 >nul
echo ==========================================
echo FinAgent Pro - 项目初始化脚本
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.10+
    exit /b 1
)

echo [1/5] 创建Python虚拟环境...
cd %~dp0\..
python -m venv venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    exit /b 1
)

echo [2/5] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [3/5] 安装后端依赖...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 安装后端依赖失败
    exit /b 1
)
cd ..

echo [4/5] 复制环境变量文件...
if not exist backend\.env (
    copy backend\.env.example backend\.env
    echo [提示] 请编辑 backend\.env 文件，填入你的API Key
)

echo [5/5] 安装前端依赖...
cd frontend
npm install
if errorlevel 1 (
    echo [警告] 前端依赖安装失败，请手动运行: cd frontend && npm install
)
cd ..

echo.
echo ==========================================
echo 初始化完成！
echo ==========================================
echo.
echo 下一步操作：
echo 1. 编辑 backend\.env 文件，填入你的API Key
echo 2. 运行 scripts\start.bat 启动服务
echo.
pause
