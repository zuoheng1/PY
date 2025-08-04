#!/bin/bash

# 404链接检测器 - 自动安装和启动脚本
# 使用方法: ./setup_and_run.sh [域名]

set -e  # 遇到错误时退出

echo "🚀 404链接检测器 - 自动安装和启动脚本"
echo "==========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 当前工作目录: $SCRIPT_DIR"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

echo "✅ Python3 已安装: $(python3 --version)"

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: 未找到pip3，请先安装pip3"
    exit 1
fi

echo "✅ pip3 已安装: $(pip3 --version)"

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 检查是否需要安装依赖
DEPS_INSTALLED_FLAG="venv/.deps_installed"
if [ ! -f "$DEPS_INSTALLED_FLAG" ] || [ "requirements.txt" -nt "$DEPS_INSTALLED_FLAG" ]; then
    echo "📦 安装Python依赖..."
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo "✅ 依赖安装完成"
        
        # 创建标记文件
        touch "$DEPS_INSTALLED_FLAG"
    else
        echo "⚠️  警告: 未找到requirements.txt文件，手动安装依赖..."
        pip install requests beautifulsoup4 openpyxl lxml
        touch "$DEPS_INSTALLED_FLAG"
    fi
else
    echo "✅ 依赖已是最新版本，跳过安装"
fi

# 检查主程序文件是否存在
if [ ! -f "find_404_links.py" ]; then
    echo "❌ 错误: 未找到find_404_links.py文件"
    echo "请确保该文件存在于当前目录中"
    exit 1
fi

echo "✅ 所有准备工作完成！"
echo ""

# 启动程序
echo "🎯 启动404链接检测器..."
echo "==========================================="

# 如果提供了域名参数，直接使用；否则交互式输入
if [ $# -eq 1 ]; then
    DOMAIN="$1"
    echo "使用提供的域名: $DOMAIN"
    
    # 创建临时输入文件
    TEMP_INPUT=$(mktemp)
    echo "$DOMAIN" > "$TEMP_INPUT"
    echo "100" >> "$TEMP_INPUT"  # 默认最大页面数
    echo "1" >> "$TEMP_INPUT"    # 默认延迟时间
    
    python find_404_links.py < "$TEMP_INPUT"
    rm "$TEMP_INPUT"
else
    # 交互式运行
    python find_404_links.py
fi

echo ""
echo "🎉 404链接检测完成！"
echo "📊 检查生成的Excel报告文件"