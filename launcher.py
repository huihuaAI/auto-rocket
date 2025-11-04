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
        error_msg = f"启动GUI失败: {e}"
        print(error_msg)
        import traceback
        tb_str = traceback.format_exc()
        print(tb_str)

        # 如果作为 .app 运行（没有终端），显示错误对话框
        if not has_terminal():
            try:
                import tkinter as tk
                from tkinter import messagebox, scrolledtext

                # 创建错误窗口
                error_root = tk.Tk()
                error_root.title("RocketGo - 启动错误")
                error_root.geometry("600x400")

                # 错误信息
                tk.Label(error_root, text="应用启动失败",
                        font=('Arial', 14, 'bold'), fg='red').pack(pady=10)

                # 详细错误
                text_frame = tk.Frame(error_root)
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

                error_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
                error_text.pack(fill=tk.BOTH, expand=True)
                error_text.insert(tk.END, f"错误信息:\n{error_msg}\n\n")
                error_text.insert(tk.END, f"详细堆栈:\n{tb_str}")
                error_text.config(state=tk.DISABLED)

                # 关闭按钮
                tk.Button(error_root, text="关闭",
                         command=error_root.destroy).pack(pady=10)

                error_root.mainloop()
            except:
                pass

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


def is_bundled():
    """检测是否作为打包应用运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def has_terminal():
    """检测是否有可用的终端"""
    try:
        # 尝试获取终端大小，如果失败说明没有终端
        import os
        os.get_terminal_size()
        return True
    except:
        return False


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

    # 检测是否有终端
    has_term = has_terminal()

    # 只在有终端时打印欢迎信息
    if has_term:
        print("=" * 60)
        print("RocketGo 自动回复机器人")
        print("=" * 60)
        print(f"系统平台: {platform.system()} {platform.release()}")
        print(f"Python版本: {platform.python_version()}")
        print("=" * 60)

    # 确定启动模式
    if args.cli:
        if has_term:
            print("启动模式: CLI (命令行界面)")
            print("-" * 60)
        return launch_cli()
    else:
        # 默认GUI模式
        if args.gui or not args.cli:
            if has_term:
                print("启动模式: GUI (图形界面)")
                print("-" * 60)

            # 如果GUI不可用
            if not check_gui_support():
                # 如果有终端，询问用户
                if has_term:
                    try:
                        response = input("GUI不可用，是否使用CLI模式? (y/n): ")
                        if response.lower() in ['y', 'yes']:
                            return launch_cli()
                        else:
                            return 1
                    except (EOFError, OSError):
                        # input() 失败，直接返回错误
                        print("错误: GUI不可用且无法接收输入")
                        return 1
                else:
                    # 没有终端（作为.app启动），无法询问，直接显示错误对话框
                    try:
                        import tkinter as tk
                        from tkinter import messagebox
                        root = tk.Tk()
                        root.withdraw()
                        messagebox.showerror(
                            "启动错误",
                            "无法启动GUI模式：未安装tkinter\n\n"
                            "请从终端使用 --cli 参数启动命令行模式"
                        )
                        root.destroy()
                    except:
                        pass
                    return 1

            return launch_gui()


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        # 最后的安全网：捕获未处理的异常
        import traceback
        error_msg = f"应用发生未处理的错误: {e}"
        tb_str = traceback.format_exc()

        # 尝试写入日志文件
        try:
            import os
            log_path = os.path.expanduser("~/RocketGo_crash.log")
            with open(log_path, 'w') as f:
                f.write(f"{error_msg}\n\n{tb_str}")
            print(f"错误日志已保存到: {log_path}")
        except:
            pass

        # 如果没有终端，显示错误对话框
        if not has_terminal():
            try:
                import tkinter as tk
                from tkinter import scrolledtext

                error_root = tk.Tk()
                error_root.title("RocketGo - 严重错误")
                error_root.geometry("600x400")

                tk.Label(error_root, text="应用崩溃",
                        font=('Arial', 14, 'bold'), fg='red').pack(pady=10)

                text_frame = tk.Frame(error_root)
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

                error_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
                error_text.pack(fill=tk.BOTH, expand=True)
                error_text.insert(tk.END, f"{error_msg}\n\n详细信息:\n{tb_str}")
                error_text.config(state=tk.DISABLED)

                tk.Button(error_root, text="关闭",
                         command=error_root.destroy).pack(pady=10)

                error_root.mainloop()
            except:
                pass
        else:
            print(error_msg)
            print(tb_str)

        sys.exit(1)
