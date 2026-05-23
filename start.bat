@echo off
chcp 65001 > nul
echo ========================================
echo    CodePilgrim AI Tutor 一键启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] 正在启动后端服务 (FastAPI)...
start "CodePilgrim-Backend" cmd /k "cd /d \"%~dp0backend\" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak > nul

echo [2/4] 正在启动前端服务 (Vite)...
start "CodePilgrim-Frontend" cmd /k "cd /d \"%~dp0frontend\" && npm run dev"

timeout /t 2 /nobreak > nul

echo [3/4] 正在启动本地 Agent (可选)...
pip show aiohttp > nul 2>&1
if %errorlevel% equ 0 (
    start "CodePilgrim-Agent" cmd /k "cd /d \"%~dp0agent\" && python agent.py"
    echo   Agent 已启动 (ws://127.0.0.1:18765)
) else (
    echo   跳过 Agent (aiohttp 未安装，运行: pip install aiohttp)
)

timeout /t 2 /nobreak > nul

echo [4/4] 正在打开浏览器...
start http://localhost:5173

echo.
echo ========================================
echo    启动完成！
echo ========================================
echo.
echo  后端地址:  http://localhost:8000
echo  前端地址:  http://localhost:5173
echo  API文档:   http://localhost:8000/docs
echo  Agent地址: ws://127.0.0.1:18765
echo.
echo  执行引擎:
echo    浏览器 WASM - 点击运行时自动加载
echo    本地 Agent  - 可选，需安装 aiohttp
echo    服务端执行  - 兜底保障
echo.
echo  按任意键关闭此窗口...
pause > nul
