@echo off
chcp 65001 >nul
title Bio-Graph Agent 启动器

echo ==================================================
echo  🧬 欢迎使用 Bio-Graph Agent (基于腾讯混元 Hy3)
echo ==================================================
echo 🚀 正在唤醒底层子系统并启动 Web 服务...

:: 通过 wsl 命令直接在目标路径运行 streamlit
wsl -e bash -c "cd ~/Bio_RAG_Hy3 && streamlit run app.py"

pause