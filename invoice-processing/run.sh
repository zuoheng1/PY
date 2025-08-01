#!/bin/bash
cd "$(dirname "$0")"

# 检查虚拟环境是否存在，不存在则创建
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查是否需要安装依赖
if [ ! -f "venv/.deps_installed" ]; then
    echo "安装依赖..."
    pip install -r requirements.txt
    touch venv/.deps_installed
    echo "依赖安装完成"
fi

# 运行脚本
echo "运行 zoey.py..."
python3 zoey.py