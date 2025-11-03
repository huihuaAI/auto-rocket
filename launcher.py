#!/usr/bin/env python3
"""
RocketGo 自动回复机器人 - 统一启动器

支持多种启动模式:
- GUI模式 (默认): 图形界面
- CLI模式: 命令行界面
"""

import sys
import argparse
import platform


def check_gui_support():
    """检查GUI支持"""
    try:
        import tkinter
        return True
    except ImportError:
        return False


def launch_gui():
    """启动GUI模式"""
    if not check_gui_support():
        print("错误: 未安装tkinter，无法启动GUI模式")
        print("请安装tkinter:")
        if platform.system() == "Darwin":  # macOS
            print("  brew install python-tk")
        elif platform.system() == "Linux":
            print("  sudo apt-get install python3-tk  # Debian/Ubuntu")
            print("  sudo yum install python3-tkinter  # CentOS/RHEL")
        return 1

    try:
        from gui import main as gui_main
        gui_main()
        return 0
    except Exception as e:
        print(f"启动GUI失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def launch_cli():
    """启动CLI模式"""
    try:
        import asyncio
        from main import main as cli_main
        exit_code = asyncio.run(cli_main())
        return exit_code
    except KeyboardInterrupt:
        print("\n程序已手动终止")
        return 0
    except Exception as e:
        print(f"程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RocketGo 自动回复机器人",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s              # 启动GUI模式 (默认)
  %(prog)s --gui        # 启动GUI模式
  %(prog)s --cli        # 启动CLI模式 (无界面)
  %(prog)s --headless   # 启动CLI模式 (无界面，同--cli)

环境变量配置:
  export ROCKETGO_USER="your_username"
  export ROCKETGO_PASS="your_password"
  export DIFY_API_KEY="your_dify_api_key"
        """
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--gui',
        action='store_true',
        help='启动GUI模式 (图形界面)'
    )
    mode_group.add_argument(
        '--cli', '--headless',
        action='store_true',
        help='启动CLI模式 (命令行界面，无GUI)'
    )

    args = parser.parse_args()

    # 打印欢迎信息
    print("=" * 60)
    print("RocketGo 自动回复机器人")
    print("=" * 60)
    print(f"系统平台: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    print("=" * 60)

    # 确定启动模式
    if args.cli:
        print("启动模式: CLI (命令行界面)")
        print("-" * 60)
        return launch_cli()
    else:
        # 默认GUI模式
        if args.gui or not args.cli:
            print("启动模式: GUI (图形界面)")
            print("-" * 60)
            # 如果GUI不可用，提示是否使用CLI
            if not check_gui_support():
                response = input("GUI不可用，是否使用CLI模式? (y/n): ")
                if response.lower() in ['y', 'yes']:
                    return launch_cli()
                else:
                    return 1
            return launch_gui()


if __name__ == "__main__":
    sys.exit(main())
