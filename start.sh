#!/bin/bash
# RocketGo 自动回复机器人 - macOS/Linux启动脚本

echo "========================================"
echo "RocketGo 自动回复机器人"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未检测到Python 3，请先安装Python 3.8+"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS安装命令: brew install python3"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Ubuntu/Debian: sudo apt-get install python3"
        echo "CentOS/RHEL: sudo yum install python3"
    fi
    exit 1
fi

# 显示Python版本
python_version=$(python3 --version)
echo "检测到 $python_version"
echo ""

# 显示菜单
echo "请选择启动模式:"
echo "[1] GUI模式 (图形界面)"
echo "[2] CLI模式 (命令行)"
echo "[3] 退出"
echo ""

read -p "请输入选项 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "启动GUI模式..."
        python3 launcher.py --gui
        ;;
    2)
        echo ""
        echo "启动CLI模式..."
        python3 launcher.py --cli
        ;;
    3)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项，默认启动GUI模式..."
        python3 launcher.py --gui
        ;;
esac
