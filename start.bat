@echo off
chcp 65001 >nul
title Bio-Graph Agent 启动器

echo ==================================================
echo  🧬 欢迎使用 Bio-Graph Agent (基于大模型引擎)
echo ==================================================
echo 🚀 正在唤醒底层子系统并启动 Web 服务...

:: 1. 智能检测并激活虚拟环境 (支持常见的 venv 或 .venv 文件夹)
if exist "venv\Scripts\activate.bat" (
    echo 🔄 检测到本地虚拟环境 (venv)，正在自动激活...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo 🔄 检测到本地虚拟环境 (.venv)，正在自动激活...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️ 未检测到本地虚拟环境，将尝试使用全局 Python 环境...
)

echo.
echo 🌐 引擎启动中，网页将在您的系统默认浏览器中自动打开...
echo 💡 提示：如果浏览器未自动打开，请手动访问 http://localhost:8501
echo.

:: 2. 检查是否安装了 Streamlit
where streamlit >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 严重错误: 找不到 streamlit 命令！
    echo 请确保您已经正确安装了 Python，并且在当前目录下运行过:
    echo pip install -r requirements.txt
    echo.
    pause
    exit /b
)

:: 3. 启动应用
streamlit run app.py

pause