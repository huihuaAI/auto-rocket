#!/usr/bin/env python3
"""
RocketGo 自动回复机器人 - GUI界面

跨平台Tkinter界面，支持Windows和macOS
"""

import asyncio
import logging
import os
import platform
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, scrolledtext, messagebox, filedialog
from typing import Optional

from client import RocketGoClient
from config import Config
from logger_config import setup_logging


class TextHandler(logging.Handler):
    """自定义日志处理器，将日志输出到Text widget"""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            # 自动滚动到底部
            self.text_widget.see(tk.END)

        # 在主线程中执行
        self.text_widget.after(0, append)


class ConfigFrame(ttk.LabelFrame):
    """配置管理面板"""

    def __init__(self, parent):
        super().__init__(parent, text="配置管理", padding=10)
        self.config_vars = {}
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """设置UI"""
        # RocketGo 配置
        rocketgo_frame = ttk.LabelFrame(self, text="RocketGo 配置", padding=5)
        rocketgo_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 用户名
        ttk.Label(rocketgo_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.config_vars['username'] = tk.StringVar()
        ttk.Entry(rocketgo_frame, textvariable=self.config_vars['username'], width=30).grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5
        )

        # 密码
        ttk.Label(rocketgo_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.config_vars['password'] = tk.StringVar()
        ttk.Entry(rocketgo_frame, textvariable=self.config_vars['password'],
                  show='*', width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # INPUT_PARAMS 配置
        input_params_frame = ttk.LabelFrame(self, text="AI 配置", padding=5)
        input_params_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 注册链接
        ttk.Label(input_params_frame, text="注册链接:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.config_vars['input_register_url'] = tk.StringVar()
        ttk.Entry(input_params_frame, textvariable=self.config_vars['input_register_url'],
                  width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # WhatsApp链接
        ttk.Label(input_params_frame, text="WhatsApp链接:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.config_vars['input_whatsapp_url'] = tk.StringVar()
        ttk.Entry(input_params_frame, textvariable=self.config_vars['input_whatsapp_url'],
                  width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # 客服名称
        ttk.Label(input_params_frame, text="客服名称:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.config_vars['input_hr_name'] = tk.StringVar()
        ttk.Entry(input_params_frame, textvariable=self.config_vars['input_hr_name'],
                  width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # 语言
        ttk.Label(input_params_frame, text="语言:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.config_vars['input_language'] = tk.StringVar()
        ttk.Entry(input_params_frame, textvariable=self.config_vars['input_language'],
                  width=30).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # Dify 配置
        dify_frame = ttk.LabelFrame(self, text="Dify AI 配置(谨慎修改)", padding=5)
        dify_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # API URL
        ttk.Label(dify_frame, text="API URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.config_vars['dify_url'] = tk.StringVar()
        ttk.Entry(dify_frame, textvariable=self.config_vars['dify_url'], width=30).grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5
        )

        # API Key
        ttk.Label(dify_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.config_vars['dify_api_key'] = tk.StringVar()
        ttk.Entry(dify_frame, textvariable=self.config_vars['dify_api_key'],
                  width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        
        # 日志配置
        log_frame = ttk.LabelFrame(self, text="日志配置", padding=5)
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        ttk.Label(log_frame, text="日志级别:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.config_vars['log_level'] = tk.StringVar()
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        ttk.Combobox(log_frame, textvariable=self.config_vars['log_level'],
                     values=log_levels, state='readonly', width=28).grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5
        )

        # 按钮
        button_frame = ttk.Frame(self)
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)

        ttk.Button(button_frame, text="保存配置",
                   command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置配置",
                   command=self.load_config).pack(side=tk.LEFT, padx=5)

    def load_config(self):
        """从Config类加载配置"""
        self.config_vars['username'].set(Config.USERNAME)
        self.config_vars['password'].set(Config.PASSWORD)
        self.config_vars['dify_url'].set(Config.DIFY_URL)
        self.config_vars['dify_api_key'].set(Config.DIFY_API_KEY)

        # 加载INPUT_PARAMS配置
        self.config_vars['input_register_url'].set(Config.INPUT_PARAMS.get('register_url', ''))
        self.config_vars['input_whatsapp_url'].set(Config.INPUT_PARAMS.get('whatsapp_url', ''))
        self.config_vars['input_hr_name'].set(Config.INPUT_PARAMS.get('hr_name', ''))
        self.config_vars['input_language'].set(Config.INPUT_PARAMS.get('language', ''))

        self.config_vars['log_level'].set(Config.LOG_LEVEL)

    def save_config(self):
        """保存配置到环境变量和Config类"""
        try:
            # 更新Config类
            Config.USERNAME = self.config_vars['username'].get()
            Config.PASSWORD = self.config_vars['password'].get()
            Config.DIFY_URL = self.config_vars['dify_url'].get()
            Config.DIFY_API_KEY = self.config_vars['dify_api_key'].get()

            # 更新INPUT_PARAMS配置
            Config.INPUT_PARAMS['register_url'] = self.config_vars['input_register_url'].get()
            Config.INPUT_PARAMS['whatsapp_url'] = self.config_vars['input_whatsapp_url'].get()
            Config.INPUT_PARAMS['hr_name'] = self.config_vars['input_hr_name'].get()
            Config.INPUT_PARAMS['language'] = self.config_vars['input_language'].get()
            # is_return_visit 保持默认值 0，不允许修改

            Config.LOG_LEVEL = self.config_vars['log_level'].get()

            # 同时更新环境变量（可选）
            os.environ['ROCKETGO_USER'] = Config.USERNAME
            os.environ['ROCKETGO_PASS'] = Config.PASSWORD
            os.environ['DIFY_URL'] = Config.DIFY_URL
            os.environ['DIFY_API_KEY'] = Config.DIFY_API_KEY

            # 更新INPUT_PARAMS环境变量
            os.environ['INPUT_REGISTER_URL'] = Config.INPUT_PARAMS['register_url']
            os.environ['INPUT_WHATSAPP_URL'] = Config.INPUT_PARAMS['whatsapp_url']
            os.environ['INPUT_HR_NAME'] = Config.INPUT_PARAMS['hr_name']
            os.environ['INPUT_LANGUAGE'] = Config.INPUT_PARAMS['language']
            # INPUT_IS_RETURN_VISIT 保持默认值 0

            os.environ['LOG_LEVEL'] = Config.LOG_LEVEL

            messagebox.showinfo("成功", "配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")


class ControlFrame(ttk.LabelFrame):
    """控制面板"""

    def __init__(self, parent, on_start, on_stop):
        super().__init__(parent, text="控制面板", padding=10)
        self.on_start = on_start
        self.on_stop = on_stop
        self.running = False
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 状态指示器
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=5)

        ttk.Label(status_frame, text="运行状态:").pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(status_frame, text="已停止",
                                       foreground="red", font=('', 10, 'bold'))
        self.status_label.pack(side=tk.LEFT, padx=5)

        # 控制按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=5)

        self.start_button = ttk.Button(button_frame, text="启动",
                                        command=self.start, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="停止",
                                       command=self.stop, width=15, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def start(self):
        """启动"""
        self.running = True
        self.status_label.config(text="运行中", foreground="green")
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.on_start()

    def stop(self):
        """停止"""
        self.running = False
        self.status_label.config(text="已停止", foreground="red")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.on_stop()


class LogFrame(ttk.LabelFrame):
    """日志显示面板"""

    def __init__(self, parent):
        super().__init__(parent, text="运行日志", padding=5)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            width=80,
            height=20,
            state='disabled',
            font=('Courier', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 按钮框架
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="清空日志",
                   command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出日志",
                   command=self.export_log).pack(side=tk.LEFT, padx=5)

    def clear_log(self):
        """清空日志"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

    def export_log(self):
        """导出日志到文件"""
        filename = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"日志已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出日志失败: {e}")


class RocketGoGUI:
    """主GUI应用"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RocketGo 自动回复机器人")
        self.root.geometry("900x800")

        # 设置平台特定的样式
        self.setup_platform_style()

        # 机器人客户端
        self.client: Optional[RocketGoClient] = None
        self.bot_thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # 设置UI
        self.setup_ui()

        # 设置日志处理器
        self.setup_logging()

        # 处理窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_platform_style(self):
        """设置平台特定的样式"""
        system = platform.system()

        if system == "Darwin":  # macOS
            # macOS 使用原生样式
            style = ttk.Style()
            style.theme_use('aqua')
        elif system == "Windows":
            # Windows 使用 vista 或 winnative
            style = ttk.Style()
            try:
                style.theme_use('vista')
            except:
                style.theme_use('winnative')
        else:  # Linux
            style = ttk.Style()
            style.theme_use('clam')

    def setup_ui(self):
        """设置主界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)

        # 左侧面板 - 配置和控制
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_panel.rowconfigure(0, weight=1)
        left_panel.columnconfigure(0, weight=1)

        # 配置面板
        self.config_frame = ConfigFrame(left_panel)
        self.config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # 控制面板
        self.control_frame = ControlFrame(left_panel, self.start_bot, self.stop_bot)
        self.control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N))

        # 右侧面板 - 日志
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)

        # 日志面板
        self.log_frame = LogFrame(right_panel)
        self.log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_bar = ttk.Label(
            self.root,
            text="就绪",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def setup_logging(self):
        """设置日志系统"""
        # 先设置标准日志配置（这会清除所有现有的处理器）
        setup_logging(Config.LOG_LEVEL, Config.LOG_FILE, use_colors=False)

        # 然后创建并添加文本处理器（用于GUI显示）
        text_handler = TextHandler(self.log_frame.log_text)
        text_handler.setLevel(logging.DEBUG)

        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        text_handler.setFormatter(formatter)

        # 添加到根日志记录器
        logging.getLogger().addHandler(text_handler)

    def start_bot(self):
        """启动机器人"""
        try:
            self.update_status("正在启动机器人...")

            # 在新线程中运行异步事件循环
            self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
            self.bot_thread.start()

            self.update_status("机器人已启动")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {e}")
            self.control_frame.stop()

    def run_bot(self):
        """在新线程中运行机器人"""
        try:
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # 创建客户端
            self.client = RocketGoClient()

            # 运行客户端
            self.loop.run_until_complete(self.client.start_auto_reply())
        except Exception as e:
            error_msg = str(e)
            logging.error(f"机器人运行错误: {error_msg}", exc_info=True)
            # 在主线程中更新UI
            self.root.after(0, lambda: self.control_frame.stop())
            self.root.after(0, lambda: self.update_status(f"错误: {error_msg}"))
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    def stop_bot(self):
        """停止机器人"""
        try:
            self.update_status("正在停止机器人...")

            if self.client and self.loop:
                # 在事件循环中调度清理，并等待其完成
                future = asyncio.run_coroutine_threadsafe(self.client.cleanup(), self.loop)

                # 等待清理完成（最多等待10秒）
                try:
                    future.result(timeout=10)
                except Exception as e:
                    logging.error(f"清理资源时出错: {e}", exc_info=True)

                # 清理完成后再停止事件循环
                self.loop.call_soon_threadsafe(self.loop.stop)

            # 等待线程结束
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=5)

            self.client = None
            self.loop = None
            self.bot_thread = None

            self.update_status("机器人已停止")
        except Exception as e:
            error_msg = str(e)
            logging.error(f"停止机器人错误: {error_msg}", exc_info=True)
            messagebox.showerror("错误", f"停止失败: {error_msg}")

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.config(text=f"{datetime.now().strftime('%H:%M:%S')} - {message}")

    def on_closing(self):
        """处理窗口关闭事件"""
        if self.control_frame.running:
            if messagebox.askokcancel("退出", "机器人正在运行，确定要退出吗?"):
                self.stop_bot()
                self.root.destroy()
        else:
            self.root.destroy()

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    app = RocketGoGUI()
    app.run()


if __name__ == "__main__":
    main()
