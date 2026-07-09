#!/bin/bash

echo "=================================================="
echo " 🧬 欢迎使用 Bio-Graph Agent (基于腾讯混元 Hy3) "
echo "=================================================="
echo "🚀 正在启动后台服务与网页端..."
echo "🌐 网页将在 3 秒后自动打开..."
echo "--------------------------------------------------"

# 智能识别操作系统并后台倒数 3 秒打开浏览器
if grep -qEi "(Microsoft|WSL)" /proc/version &> /dev/null; then
    # 如果是 WSL 环境，调用 Windows 的 explorer.exe
    (sleep 3 && explorer.exe "http://localhost:8501") &
else
    # 如果是纯正的 Linux 环境，调用 xdg-open
    (sleep 3 && xdg-open "http://localhost:8501") &
fi

# 启动 Streamlit
~/miniconda3/envs/py310/bin/streamlit run app.py