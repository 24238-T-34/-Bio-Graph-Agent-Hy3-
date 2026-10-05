@echo off
chcp 65001 >nul
title Bio-Graph Agent 启动器

echo ==================================================
echo  🧬 欢迎使用 Bio-Graph Agent (基于腾讯混元 Hy3)
echo ==================================================
echo 🚀 正在唤醒底层子系统并启动 Web 服务...
echo 🌐 网页将在 3 秒后自动在 Windows 默认浏览器中打开...

:: 将后台运行符 & 放在括号内，确保 cd 命令对后面的 streamlit 依然生效
wsl -e bash -c "cd ~/Bio_RAG_Hy3 && (sleep 3 && explorer.exe 'http://localhost:8501' &) && ~/miniconda3/envs/py310/bin/streamlit run app.py"

pause