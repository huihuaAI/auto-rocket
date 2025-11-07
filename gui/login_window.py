#!/usr/bin/env python3
"""
登录窗口 - 用户登录界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import logging
from config import config, set_credentials, get_credentials

logger = logging.getLogger(__name__)


class LoginWindow:
    """登录窗口

    功能：
    - 用户名密码输入
    - 记住密码功能
    - 登录按钮
    """

    def __init__(self, on_login_success):
        """初始化登录窗口

        Args:
            on_login_success: 登录成功回调函数 callback(username, password)
        """
        self.on_login_success = on_login_success

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("RocketGo 自动控制系统 - 登录")
        self.root.geometry("400x300")
        self.root.resizable(False, False)

        # 居中显示
        self._center_window()

        # 创建UI
        self._create_widgets()

        # 加载保存的凭据
        self._load_credentials()

    def _center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 标题
        title_label = ttk.Label(main_frame, text="RocketGo 自动控制系统",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 30))

        # 用户名
        ttk.Label(main_frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=30)
        username_entry.grid(row=1, column=1, pady=5, padx=(10, 0))

        # 密码
        ttk.Label(main_frame, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(main_frame, textvariable=self.password_var,
                                    show="*", width=30)
        password_entry.grid(row=2, column=1, pady=5, padx=(10, 0))

        # 记住密码
        self.remember_var = tk.BooleanVar(value=True)
        remember_check = ttk.Checkbutton(main_frame, text="记住密码",
                                         variable=self.remember_var)
        remember_check.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # 登录按钮
        self.login_button = ttk.Button(main_frame, text="登录",
                                       command=self._on_login_click)
        self.login_button.grid(row=4, column=0, columnspan=2, pady=(20, 0))

        # 状态标签
        self.status_var = tk.StringVar(value="请输入用户名和密码")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                 foreground="gray")
        status_label.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        # 绑定回车键
        password_entry.bind('<Return>', lambda e: self._on_login_click())

    def _load_credentials(self):
        """加载保存的凭据"""
        try:
            # 尝试从keyring加载最后使用的用户名
            # 这里我们假设配置文件中可能保存了上次的用户名
            # 实际使用中可以从配置文件或其他地方读取
            pass
        except Exception as e:
            logger.debug(f"加载凭据失败: {e}")

    def _on_login_click(self):
        """登录按钮点击事件"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return

        # 禁用登录按钮，防止重复点击
        self.login_button.config(state='disabled')
        self.status_var.set("正在登录...")

        # 异步执行登录
        asyncio.create_task(self._do_login(username, password))

    async def _do_login(self, username: str, password: str):
        """执行登录

        Args:
            username: 用户名
            password: 密码
        """
        try:
            # 调用登录回调
            success = await self.on_login_success(username, password)

            if success:
                # 保存凭据（如果勾选了记住密码）
                if self.remember_var.get():
                    try:
                        set_credentials(username, password)
                    except Exception as e:
                        logger.error(f"保存凭据失败: {e}")

                self.status_var.set("登录成功！")

                # 延迟关闭窗口
                self.root.after(500, self._close_and_continue)
            else:
                self.status_var.set("登录失败，请检查用户名和密码")
                self.login_button.config(state='normal')
                messagebox.showerror("登录失败", "用户名或密码错误，请重试")

        except Exception as e:
            logger.error(f"登录出错: {e}", exc_info=True)
            self.status_var.set("登录出错")
            self.login_button.config(state='normal')
            messagebox.showerror("错误", f"登录过程出错: {str(e)}")

    def _close_and_continue(self):
        """关闭登录窗口并继续"""
        self.root.quit()
        self.root.destroy()

    def run(self):
        """运行登录窗口"""
        self.root.mainloop()
