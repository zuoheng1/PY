#!/bin/bash

# 404链接检测器 - 简化版启动脚本
# 使用方法: ./setup_and_run.sh

set -e  # 遇到错误时退出

echo "🚀 404链接检测器 - 简化版启动脚本"
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

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "📝 首次运行，将创建默认配置文件"
    echo "💡 程序会自动创建config.json，请根据需要修改配置"
else
    echo "✅ 配置文件已存在: config.json"
    echo "📋 当前配置:"
    if command -v jq &> /dev/null; then
        # 如果安装了jq，美化显示JSON
        cat config.json | jq .
    else
        # 否则直接显示
        cat config.json
    fi
fi

echo "✅ 所有准备工作完成！"
echo ""

# 启动程序
echo "🎯 启动404链接检测器..."
echo "==========================================="

# 直接运行主程序（配置通过config.json文件读取）
python3 find_404_links.py

echo ""
echo "🎉 404链接检测完成！"
echo "📂 检查reports目录中生成的报告文件"
echo "📊 包含Excel、HTML和JSON格式的报告"

# 显示生成的文件
if [ -d "reports" ]; then
    echo ""
    echo "📋 生成的报告文件:"
    ls -la reports/
fi

# 退出虚拟环境
deactivate