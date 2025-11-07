#!/usr/bin/env python3
"""
主窗口 - 应用主界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import logging
from typing import Optional
from datetime import datetime

from services.rocket_service import RocketService, ServiceStatus
from services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


class MainWindow:
    """主窗口

    功能：
    - 服务控制（启动/停止/重启）
    - 配置编辑
    - 日志查看
    - 定时重启控制
    - 对话监听服务控制
    """

    def __init__(self, rocket_service: RocketService):
        """初始化主窗口

        Args:
            rocket_service: RocketGo服务实例
        """
        self.rocket_service = rocket_service
        self.scheduler_service: Optional[SchedulerService] = None

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("RocketGo 自动控制系统")
        self.root.geometry("1000x700")

        # 设置最小尺寸
        self.root.minsize(800, 600)

        # 创建UI
        self._create_widgets()

        # 设置关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 启动状态更新定时器
        self._start_status_update_timer()

    def _create_widgets(self):
        """创建UI组件"""
        # 创建菜单栏
        self._create_menu()

        # 创建主容器（使用PanedWindow实现可调整大小）
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧面板 - 控制和配置
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # 右侧面板 - 日志查看
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # 创建左侧内容
        self._create_left_panel(left_frame)

        # 创建右侧内容
        self._create_right_panel(right_frame)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="退出", command=self._on_closing)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _create_left_panel(self, parent):
        """创建左侧面板"""
        # 使用Notebook创建标签页
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 控制面板标签页
        control_frame = ttk.Frame(notebook)
        notebook.add(control_frame, text="控制面板")
        self._create_control_panel(control_frame)

        # 配置面板标签页
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="配置编辑")
        self._create_config_panel(config_frame)

    def _create_control_panel(self, parent):
        """创建控制面板"""
        # 服务状态
        status_frame = ttk.LabelFrame(parent, text="服务状态", padding="10")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_var = tk.StringVar(value="未启动")
        ttk.Label(status_frame, text="状态:").grid(row=0, column=0, sticky=tk.W, pady=2)
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                 font=('Arial', 10, 'bold'))
        status_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # 服务控制按钮
        button_frame = ttk.LabelFrame(parent, text="服务控制", padding="10")
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_button = ttk.Button(button_frame, text="启动服务",
                                       command=self._on_start_click)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)

        self.stop_button = ttk.Button(button_frame, text="停止服务",
                                      command=self._on_stop_click, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        self.restart_button = ttk.Button(button_frame, text="重启服务",
                                         command=self._on_restart_click, state='disabled')
        self.restart_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.EW)

        # 配置列权重
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        # 定时重启控制
        scheduler_frame = ttk.LabelFrame(parent, text="定时重启", padding="10")
        scheduler_frame.pack(fill=tk.X, padx=5, pady=5)

        self.scheduler_enabled_var = tk.BooleanVar(value=False)
        scheduler_check = ttk.Checkbutton(scheduler_frame, text="启用定时重启",
                                          variable=self.scheduler_enabled_var,
                                          command=self._on_scheduler_toggle)
        scheduler_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Label(scheduler_frame, text="最小间隔(小时):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.min_interval_var = tk.StringVar(value="1.0")
        min_interval_entry = ttk.Entry(scheduler_frame, textvariable=self.min_interval_var, width=10)
        min_interval_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(scheduler_frame, text="最大间隔(小时):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.max_interval_var = tk.StringVar(value="3.0")
        max_interval_entry = ttk.Entry(scheduler_frame, textvariable=self.max_interval_var, width=10)
        max_interval_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        self.next_restart_var = tk.StringVar(value="未设置")
        ttk.Label(scheduler_frame, text="下次重启:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(scheduler_frame, textvariable=self.next_restart_var).grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # 对话监听服务控制
        monitor_frame = ttk.LabelFrame(parent, text="对话监听服务", padding="10")
        monitor_frame.pack(fill=tk.X, padx=5, pady=5)

        self.monitor_enabled_var = tk.BooleanVar(value=False)
        monitor_check = ttk.Checkbutton(monitor_frame, text="启用对话监听",
                                        variable=self.monitor_enabled_var,
                                        command=self._on_monitor_toggle)
        monitor_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Label(monitor_frame, text="检查间隔(秒):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.check_interval_var = tk.StringVar(value="5")
        check_interval_entry = ttk.Entry(monitor_frame, textvariable=self.check_interval_var, width=10)
        check_interval_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(monitor_frame, text="超时阈值(小时):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.stale_hours_var = tk.StringVar(value="3")
        stale_hours_entry = ttk.Entry(monitor_frame, textvariable=self.stale_hours_var, width=10)
        stale_hours_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(monitor_frame, text="最大激活次数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.max_active_var = tk.StringVar(value="10")
        max_active_entry = ttk.Entry(monitor_frame, textvariable=self.max_active_var, width=10)
        max_active_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))

    def _create_config_panel(self, parent):
        """创建配置面板"""
        # 配置文件路径显示
        path_frame = ttk.Frame(parent)
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(path_frame, text="配置文件: config.toml").pack(side=tk.LEFT)

        # 配置编辑器
        editor_frame = ttk.Frame(parent)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.config_text = scrolledtext.ScrolledText(editor_frame, wrap=tk.WORD)
        self.config_text.pack(fill=tk.BOTH, expand=True)

        # 加载配置文件
        self._load_config_file()

        # 按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="保存配置",
                   command=self._save_config_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重新加载",
                   command=self._load_config_file).pack(side=tk.LEFT, padx=5)

    def _create_right_panel(self, parent):
        """创建右侧面板 - 日志查看"""
        # 日志查看器
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD,
                                                   state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志标签样式
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('ERROR', foreground='red')
        self.log_text.tag_config('DEBUG', foreground='gray')

        # 按钮框架
        button_frame = ttk.Frame(log_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(button_frame, text="清空日志",
                   command=self._clear_log).pack(side=tk.LEFT, padx=5)

        # 设置日志处理器
        self._setup_log_handler()

    def _load_config_file(self):
        """加载配置文件"""
        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config.toml"
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.config_text.delete('1.0', tk.END)
                self.config_text.insert('1.0', content)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            messagebox.showerror("错误", f"加载配置文件失败: {str(e)}")

    def _save_config_file(self):
        """保存配置文件"""
        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config.toml"
            content = self.config_text.get('1.0', tk.END)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("成功", "配置文件已保存！\n注意：部分配置需要重启服务才能生效。")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            messagebox.showerror("错误", f"保存配置文件失败: {str(e)}")

    def _setup_log_handler(self):
        """设置日志处理器，将日志输出到GUI"""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                tag = record.levelname

                def append():
                    self.text_widget.config(state='normal')
                    self.text_widget.insert(tk.END, msg + '\n', tag)
                    self.text_widget.see(tk.END)
                    self.text_widget.config(state='disabled')

                # 在主线程中更新GUI
                self.text_widget.after(0, append)

        handler = GUILogHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                      datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)

    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

    def _on_start_click(self):
        """启动服务按钮点击"""
        asyncio.create_task(self._start_service())

    def _on_stop_click(self):
        """停止服务按钮点击"""
        asyncio.create_task(self._stop_service())

    def _on_restart_click(self):
        """重启服务按钮点击"""
        asyncio.create_task(self._restart_service())

    async def _start_service(self):
        """启动服务"""
        try:
            self.start_button.config(state='disabled')
            await self.rocket_service.start()
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.restart_button.config(state='normal')
        except Exception as e:
            logger.error(f"启动服务失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"启动服务失败: {str(e)}")
            self.start_button.config(state='normal')

    async def _stop_service(self):
        """停止服务"""
        try:
            self.stop_button.config(state='disabled')
            await self.rocket_service.stop()
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.restart_button.config(state='disabled')
        except Exception as e:
            logger.error(f"停止服务失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"停止服务失败: {str(e)}")
            self.stop_button.config(state='normal')

    async def _restart_service(self):
        """重启服务"""
        try:
            self.restart_button.config(state='disabled')
            await self.rocket_service.restart()
            self.restart_button.config(state='normal')
        except Exception as e:
            logger.error(f"重启服务失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"重启服务失败: {str(e)}")
            self.restart_button.config(state='normal')

    def _on_scheduler_toggle(self):
        """定时重启开关切换"""
        if self.scheduler_enabled_var.get():
            asyncio.create_task(self._start_scheduler())
        else:
            asyncio.create_task(self._stop_scheduler())

    async def _start_scheduler(self):
        """启动定时重启服务"""
        try:
            min_hours = float(self.min_interval_var.get())
            max_hours = float(self.max_interval_var.get())

            if min_hours <= 0 or max_hours <= 0 or min_hours > max_hours:
                messagebox.showerror("错误", "请输入有效的时间间隔（最小值应小于最大值）")
                self.scheduler_enabled_var.set(False)
                return

            # 创建定时服务
            self.scheduler_service = SchedulerService(
                restart_callback=self.rocket_service.restart,
                min_interval_hours=min_hours,
                max_interval_hours=max_hours
            )
            self.scheduler_service.start()
            logger.info("定时重启服务已启动")

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            self.scheduler_enabled_var.set(False)
        except Exception as e:
            logger.error(f"启动定时服务失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"启动定时服务失败: {str(e)}")
            self.scheduler_enabled_var.set(False)

    async def _stop_scheduler(self):
        """停止定时重启服务"""
        try:
            if self.scheduler_service:
                await self.scheduler_service.stop()
                self.scheduler_service = None
                self.next_restart_var.set("未设置")
                logger.info("定时重启服务已停止")
        except Exception as e:
            logger.error(f"停止定时服务失败: {e}", exc_info=True)

    def _on_monitor_toggle(self):
        """对话监听开关切换"""
        if self.monitor_enabled_var.get():
            asyncio.create_task(self._start_monitor())
        else:
            asyncio.create_task(self._stop_monitor())

    async def _start_monitor(self):
        """启动对话监听服务"""
        try:
            if not self.rocket_service.is_running():
                messagebox.showerror("错误", "请先启动主服务")
                self.monitor_enabled_var.set(False)
                return

            check_interval = int(self.check_interval_var.get())
            stale_hours = int(self.stale_hours_var.get())
            max_active = int(self.max_active_var.get())

            await self.rocket_service.start_conversation_monitor(
                check_interval=check_interval,
                stale_hours=stale_hours,
                max_active_count=max_active
            )
            logger.info("对话监听服务已启动")

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            self.monitor_enabled_var.set(False)
        except Exception as e:
            logger.error(f"启动对话监听服务失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"启动对话监听服务失败: {str(e)}")
            self.monitor_enabled_var.set(False)

    async def _stop_monitor(self):
        """停止对话监听服务"""
        try:
            await self.rocket_service.stop_conversation_monitor()
            logger.info("对话监听服务已停止")
        except Exception as e:
            logger.error(f"停止对话监听服务失败: {e}", exc_info=True)

    def _start_status_update_timer(self):
        """启动状态更新定时器"""
        self._update_status()
        self.root.after(1000, self._start_status_update_timer)

    def _update_status(self):
        """更新状态显示"""
        status = self.rocket_service.status
        self.status_var.set(status.value)

        # 更新下次重启时间
        if self.scheduler_service and self.scheduler_service.is_running():
            next_time = self.scheduler_service.get_next_restart_time()
            if next_time:
                self.next_restart_var.set(next_time)

    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于",
            "RocketGo 自动控制系统\n\n"
            "版本: 1.0.0\n"
            "功能: 自动化管理RocketGo消息处理"
        )

    def _on_closing(self):
        """窗口关闭事件"""
        if self.rocket_service.is_running():
            if messagebox.askokcancel("退出", "服务正在运行，确定要退出吗？"):
                asyncio.create_task(self._cleanup_and_exit())
        else:
            self.root.quit()
            self.root.destroy()

    async def _cleanup_and_exit(self):
        """清理并退出"""
        try:
            if self.scheduler_service:
                await self.scheduler_service.stop()
            await self.rocket_service.cleanup()
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
        finally:
            self.root.quit()
            self.root.destroy()

    def run(self):
        """运行主窗口"""
        self.root.mainloop()
