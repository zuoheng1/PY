#!/bin/bash

# PDF转Word工具快速启动脚本

echo "🚀 PDF转Word转换工具"
echo "=================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "🔧 首次运行，安装依赖..."
    chmod +x install_dependencies.sh
    ./install_dependencies.sh
fi

# 激活虚拟环境
source venv/bin/activate

# 检查参数
if [ $# -eq 0 ]; then
    echo "📖 使用方法:"
    echo "  ./run.sh file.pdf                 # 转换单个文件"
    echo "  ./run.sh /path/to/pdfs/           # 转换目录"
    echo "  ./run.sh /path/to/pdfs/ -r        # 递归转换"
    echo "  ./run.sh file.pdf -m ocr         # 使用OCR"
    echo ""
    echo "📋 可用的转换方法:"
    echo "  auto     - 自动选择（默认）"
    echo "  pdf2docx - 保持格式（推荐）"
    echo "  pypdf    - 纯文本提取"
    echo "  ocr      - OCR识别（扫描版PDF）"
    echo ""
    echo "🔍 查看详细帮助: ./run.sh --help"
    exit 1
fi

# 运行转换工具
python pdf_to_word.py "$@"

echo "\n✅ 转换完成！查看output目录中的结果文件。"