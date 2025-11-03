#!/usr/bin/env python3
"""
日志配置模块 - 提供彩色和格式化的日志输出
"""

import logging
import sys

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }

    # 模块颜色映射
    MODULE_COLORS = {
        'main': '\033[94m',           # 亮蓝色
        'client': '\033[95m',         # 亮紫色
        'playwright_ws': '\033[96m',  # 亮青色
        'chat_processor': '\033[93m', # 亮黄色
        'reply_handler': '\033[92m',  # 亮绿色
        'dify_client': '\033[91m',    # 亮红色
        'db_manager': '\033[90m',     # 灰色
    }

    RESET = '\033[0m'
    BOLD = '\033[1m'

    def __init__(self, use_colors=True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record):
        if not self.use_colors:
            return self._format_plain(record)

        # 获取时间戳
        timestamp = self.formatTime(record, '%H:%M:%S')

        # 获取日志级别颜色
        level_color = self.COLORS.get(record.levelname, '')

        # 获取模块颜色
        module_name = record.name.split('.')[-1]  # 获取最后一部分作为模块名
        module_color = self.MODULE_COLORS.get(module_name, '\033[37m')  # 默认白色

        # 格式化消息
        message = record.getMessage()

        # 构建基础格式
        base_format = (f"\033[90m{timestamp}\033[0m "
                      f"{level_color}[{record.levelname}]{self.RESET} "
                      f"{module_color}{record.name}{self.RESET}: ")

        # 特殊处理不同类型的消息
        if '[浏览器]' in message:
            # 浏览器消息用特殊格式
            formatted = base_format + f"\033[96m🌐 {message}{self.RESET}"
        elif 'WebSocket' in message and ('连接' in message or '关闭' in message):
            # WebSocket连接相关消息
            formatted = base_format + f"\033[94m🔗 {message}{self.RESET}"
        elif '收到' in message and '消息' in message:
            # 消息收发
            formatted = base_format + f"\033[93m📨 {message}{self.RESET}"
        elif '发送' in message:
            # 发送消息
            formatted = base_format + f"\033[95m📤 {message}{self.RESET}"
        elif record.levelname == 'ERROR':
            # 错误消息特殊处理
            formatted = (f"\033[90m{timestamp}\033[0m "
                        f"{self.BOLD}{level_color}[{record.levelname}]{self.RESET} "
                        f"{module_color}{record.name}{self.RESET}: "
                        f"\033[91m❌ {message}{self.RESET}")
        elif record.levelname == 'WARNING':
            # 警告消息
            formatted = base_format + f"\033[93m⚠️  {message}{self.RESET}"
        elif record.levelname == 'INFO' and ('成功' in message or '完成' in message or '✅' in message):
            # 成功消息
            formatted = base_format + f"\033[92m✅ {message}{self.RESET}"
        else:
            # 普通消息
            formatted = base_format + message

        return formatted

    def _format_plain(self, record):
        """纯文本格式（无颜色）"""
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        return f"{timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"

def setup_logging(log_level="INFO", log_file="auto_reply.log", use_colors=True):
    """设置彩色日志系统"""

    # 清除已有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 设置日志级别
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 控制台处理器（彩色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（纯文本）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = ColoredFormatter(use_colors=False)  # 文件不使用颜色
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    return root_logger

def print_startup_banner():
    """打印启动横幅"""
    banner = """
\033[96m╔══════════════════════════════════════════════════════════════╗
║                    🤖 RocketGo 自动回复机器人                    ║
╠══════════════════════════════════════════════════════════════╣
║  功能: 智能监听 → AI对话 → 自动回复                              ║
║  技术: Playwright + Dify AI + SQLite                         ║
║  状态: 正在启动...                                             ║
╚══════════════════════════════════════════════════════════════╝\033[0m
"""
    print(banner)

def print_status_message(message: str, status: str = "info"):
    """打印状态消息"""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "loading": "⏳"
    }

    colors = {
        "info": "\033[94m",
        "success": "\033[92m",
        "warning": "\033[93m",
        "error": "\033[91m",
        "loading": "\033[96m"
    }

    icon = icons.get(status, "ℹ️")
    color = colors.get(status, "\033[94m")

    print(f"{color}{icon} {message}\033[0m")

if __name__ == "__main__":
    # 测试彩色日志
    setup_logging("DEBUG", use_colors=True)

    logger = logging.getLogger("test_module")

    print_startup_banner()
    print_status_message("开始测试日志系统", "loading")

    logger.debug("这是调试信息")
    logger.info("系统启动成功")
    logger.info("✅ 连接建立成功")
    logger.warning("检测到网络延迟")
    logger.error("连接失败")
    logger.info("收到WebSocket消息: {'sendType': 1}")
    logger.debug("[浏览器] 📨 收到WebSocket消息: {'sendType': 1}")

    print_status_message("日志测试完成", "success")