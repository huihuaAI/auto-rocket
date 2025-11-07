#!/usr/bin/env python3
"""
RocketGo 自动控制系统 - 主入口文件

功能：
1. 用户登录
2. 启动主界面
3. 集成 asyncio 和 tkinter
"""

import sys
import asyncio
import logging
import tkinter as tk
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from services.rocket_service import RocketService
from gui.login_window import LoginWindow
from gui.main_window import MainWindow


def setup_logging():
    """配置日志系统"""
    from logging.handlers import TimedRotatingFileHandler

    log_level = getattr(logging, config.log.level.upper(), logging.INFO)

    # 创建按天轮转的日志处理器
    # when='midnight': 每天午夜轮转
    # interval=1: 每1天轮转一次
    # backupCount=7: 保留7天的日志
    # encoding='utf-8': 使用UTF-8编码
    file_handler = TimedRotatingFileHandler(
        filename=config.log.file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y-%m-%d"  # 日志文件后缀格式：auto_reply.log.2025-01-07

    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("RocketGo 自动控制系统启动")
    logger.info("=" * 60)


class AsyncTkApp:
    """集成 asyncio 和 tkinter 的应用程序"""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.rocket_service: RocketService = None
        self.main_window: MainWindow = None

    async def run_login(self):
        """运行登录窗口"""
        login_success = False
        username = None
        password = None

        async def on_login(user, pwd):
            nonlocal login_success, username, password
            # 创建服务并尝试登录
            self.rocket_service = RocketService()
            success = await self.rocket_service.login(user, pwd)
            if success:
                login_success = True
                username = user
                password = pwd
            return success

        # 创建登录窗口
        login_window = LoginWindow(on_login_success=on_login)

        # 在 asyncio 事件循环中运行 tkinter
        await self._run_tk_window(login_window.root)

        return login_success

    async def run_main(self):
        """运行主窗口"""
        # 创建主窗口
        self.main_window = MainWindow(self.rocket_service)

        # 在 asyncio 事件循环中运行 tkinter
        await self._run_tk_window(self.main_window.root)

    async def _run_tk_window(self, root):
        """在 asyncio 事件循环中运行 tkinter 窗口

        Args:
            root: tkinter 根窗口
        """
        try:
            while True:
                # 更新 tkinter 事件
                root.update()

                # 处理 asyncio 任务
                await asyncio.sleep(0.01)

                # 检查窗口是否被关闭
                if not root.winfo_exists():
                    break

        except tk.TclError:
            # 窗口已关闭
            pass
        except Exception as e:
            logging.error(f"窗口运行出错: {e}", exc_info=True)

    async def run(self):
        """运行应用程序"""
        try:
            # 1. 显示登录窗口
            login_success = await self.run_login()

            if not login_success:
                logging.info("用户取消登录或登录失败，程序退出")
                return

            logging.info("登录成功，启动主窗口")

            # 2. 显示主窗口
            await self.run_main()

        except KeyboardInterrupt:
            logging.info("用户中断程序")
        except Exception as e:
            logging.error(f"程序运行出错: {e}", exc_info=True)
        finally:
            # 清理资源
            if self.rocket_service:
                try:
                    await self.rocket_service.cleanup()
                except Exception as e:
                    logging.error(f"清理资源失败: {e}")

            logging.info("程序退出")

    def start(self):
        """启动应用程序"""
        try:
            self.loop.run_until_complete(self.run())
        finally:
            self.loop.close()


def main():
    """主函数"""
    # 配置日志
    setup_logging()

    # 创建并启动应用
    app = AsyncTkApp()
    app.start()


if __name__ == "__main__":
    main()
