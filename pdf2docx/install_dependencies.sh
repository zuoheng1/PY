#!/bin/bash

# PDF转Word工具依赖安装脚本

echo "🚀 PDF转Word工具 - 依赖安装脚本"
echo "======================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "📦 升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 检查Tesseract OCR（可选）
echo "🔍 检查Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract已安装: $(tesseract --version | head -1)"
else
    echo "⚠️  Tesseract未安装，OCR功能将不可用"
    echo "   macOS安装: brew install tesseract tesseract-lang"
    echo "   Ubuntu安装: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim"
fi

echo "✅ 依赖安装完成！"
echo ""
echo "📖 使用方法:"
echo "   python pdf_to_word.py --help"
echo "   python pdf_to_word.py example.pdf"
echo "   python pdf_to_word.py /path/to/pdfs/ -r"