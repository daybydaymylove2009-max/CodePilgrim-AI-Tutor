@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo    CodePilgrim AI Tutor 一键启动脚本
echo ========================================
echo.

set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"
set "LOG_DIR=%PROJECT_DIR%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "BACKEND_LOG=%LOG_DIR%\backend_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "BACKEND_LOG=%BACKEND_LOG: =0%"
set "FRONTEND_LOG=%LOG_DIR%\frontend_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "FRONTEND_LOG=%FRONTEND_LOG: =0%"

echo [1/4] 检查端口占用情况...
netstat -ano | findstr ":8000" > nul
if !errorlevel! equ 0 (
    echo   警告: 端口 8000 已被占用，后端可能启动失败
)
netstat -ano | findstr ":5173" > nul
if !errorlevel! equ 0 (
    echo   警告: 端口 5173 已被占用，前端可能启动失败
)

echo.
echo [2/4] 正在启动后端服务 (FastAPI :8000)...
echo   日志文件: %BACKEND_LOG%
start "CodePilgrim-Backend" cmd /k "cd /d \"%BACKEND_DIR%\" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2^>^&1 ^> \"%BACKEND_LOG%\""

echo.
echo [3/4] 正在启动前端服务 (Vite :5173)...
echo   日志文件: %FRONTEND_LOG%
start "CodePilgrim-Frontend" cmd /k "cd /d \"%FRONTEND_DIR%\" && npm run dev 2^>^&1 ^> \"%FRONTEND_LOG%\""

echo.
echo [4/4] 等待服务启动...
echo.

set "MAX_WAIT=10"
set "COUNT=0"

echo 正在检查后端服务状态...
:check_backend
timeout /t 2 /nobreak > nul
curl -s http://localhost:8000/health > nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] 后端服务已就绪
    goto :backend_ok
)
set /a COUNT+=1
if !COUNT! lss %MAX_WAIT% (
    goto :check_backend
)
echo   [WARN] 后端服务可能仍在启动中

:backend_ok

echo.
echo ========================================
echo    启动完成！
echo ========================================
echo.
echo   后端地址: http://localhost:8000
echo   前端地址: http://localhost:5173
echo   API文档:  http://localhost:8000/docs
echo.
echo   日志目录: %LOG_DIR%
echo.
echo  提示: 关闭此窗口不会停止服务
echo        如需停止服务，请在对应窗口按 Ctrl+C
echo.
echo  按任意键打开浏览器并结束此脚本...
pause > nul

start http://localhost:5173

endlocal
exit /b 0
