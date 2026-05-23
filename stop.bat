@echo off
chcp 65001 > nul
echo ========================================
echo    CodePilgrim AI Tutor 停止服务
echo ========================================
echo.

echo 正在停止前端服务 (Vite)...
taskkill /f /im node.exe /fi "WINDOWTITLE eq CodePilgrim-Frontend*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] 前端服务已停止
) else (
    echo   [INFO] 前端服务未在运行
)

echo.
echo 正在停止后端服务 (FastAPI)...
taskkill /f /im python.exe /fi "WINDOWTITLE eq CodePilgrim-Backend*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] 后端服务已停止
) else (
    echo   [INFO] 后端服务未在运行
)

echo.
echo 正在清理残留进程...
for /f "tokens=2" %%a in ('tasklist /fi "WINDOWTITLE eq CodePilgrim*" /fo list ^| findstr "PID"') do (
    taskkill /f /pid %%a 2>nul
)

echo.
echo ========================================
echo    所有服务已停止
echo ========================================
echo.
pause
