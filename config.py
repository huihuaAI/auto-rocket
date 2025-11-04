#!/usr/bin/env python3
"""
配置文件 - 集中管理所有配置项
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

def get_user_data_dir():
    """获取用户数据目录（跨平台）"""
    app_name = "RocketGo"

    if sys.platform == "darwin":  # macOS
        data_dir = Path.home() / "Library" / "Application Support" / app_name
    elif sys.platform == "win32":  # Windows
        data_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / app_name
    else:  # Linux and others
        data_dir = Path.home() / ".local" / "share" / app_name

    # 确保目录存在
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_bundled_resource_path(relative_path):
    """获取打包资源的路径（兼容PyInstaller）"""
    try:
        # PyInstaller 创建的临时文件夹路径
        if hasattr(sys, '_MEIPASS'):
            # 在 macOS .app 包中，资源在 Contents/Resources/
            if sys.platform == 'darwin':
                base_path = Path(sys._MEIPASS).parent / 'Resources'
            else:
                base_path = Path(sys._MEIPASS)
        else:
            # 开发环境，使用脚本所在目录
            base_path = Path(__file__).parent
    except Exception:
        base_path = Path(__file__).parent

    return base_path / relative_path

def setup_env_file():
    """确保用户数据目录有 .env 文件"""
    user_data_dir = get_user_data_dir()
    user_env_file = user_data_dir / '.env'

    # 如果用户数据目录没有 .env 文件
    if not user_env_file.exists():
        # 尝试从打包资源复制
        bundled_env = get_bundled_resource_path('.env')
        if bundled_env.exists():
            shutil.copy2(bundled_env, user_env_file)
            print(f"已从打包资源复制 .env 到: {user_env_file}")
        else:
            # 如果打包资源也没有，尝试从开发环境复制
            dev_env = Path(__file__).parent / '.env'
            if dev_env.exists():
                shutil.copy2(dev_env, user_env_file)
                print(f"已从开发环境复制 .env 到: {user_env_file}")

    return user_env_file

# 获取用户数据目录
USER_DATA_DIR = get_user_data_dir()

# 设置并加载 .env 文件
USER_ENV_FILE = setup_env_file()
load_dotenv(USER_ENV_FILE)

class Config:
    """应用配置类"""

    # --------------------------- 基础配置 ---------------------------
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
    # 使用用户数据目录作为日志文件路径
    LOG_FILE = os.getenv("LOG_FILE", None)
    if LOG_FILE and not os.path.isabs(LOG_FILE):
        # 如果是相对路径，转换为用户数据目录下的绝对路径
        LOG_FILE = str(USER_DATA_DIR / LOG_FILE)
    elif not LOG_FILE:
        # 默认使用用户数据目录
        LOG_FILE = str(USER_DATA_DIR / "auto_reply.log")

    # --------------------------- RocketGo 配置 ---------------------------
    # 登录相关URL
    LOGIN_URL = os.getenv(
        "ROCKETGO_LOGIN_URL", "https://pn3cs.rocketgo.vip/prod-api2/login"
    )
    CAPTCHA_IMAGE_URL = os.getenv(
        "ROCKETGO_CAPTCHA_IMAGE_URL", "https://pn3cs.rocketgo.vip/prod-api2/captchaImage"
    )
    USER_INFO_URL = os.getenv(
        "ROCKETGO_USER_INFO_URL", "https://pn3cs.rocketgo.vip/prod-api2/getInfo"
    )
    ACCOUNT_INFO_URL = os.getenv(
        "ROCKETGO_ACCOUNT_INFO_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/getAccountList"
    )
    SESSION_URL = os.getenv(
        "ROCKETGO_SESSION_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/getCsList"
    )
    NOT_READ_MESSAGE_URL = os.getenv(
        "NOT_READ_MESSAGE_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/getNotRead"
    )
    FRIENDS_URL = os.getenv(
        "FRIENDS_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/getAccountChat"
    )
    FRIENDS_CHAT_URL = os.getenv(
        "FRIENDS_CHAT_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/chatLogList"
    )
    WS_URL = os.getenv(
        "ROCKETGO_WS_URL", "wss://pn3cs.rocketgo.vip/websocket"
    )
    SET_READ_URL = os.getenv(
        "SET_READ_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/setRead/"
    )

    # 登录凭据
    USERNAME = os.getenv("ROCKETGO_USER", None)
    PASSWORD = os.getenv("ROCKETGO_PASS", None)

    # 连接配置
    RECONNECT_DELAY = float(os.getenv("RECONNECT_DELAY", "3.0"))

    # --------------------------- Dify AI 配置 ---------------------------
    DIFY_URL = os.getenv("DIFY_URL", None)
    DIFY_API_KEY = os.getenv("DIFY_API_KEY", None)

    # INPUT_PARAMS：从.env读取拆分的键，重新构造字典
    INPUT_PARAMS = {
        "register_url": os.getenv("INPUT_REGISTER_URL", None),
        "whatsapp_url": os.getenv("INPUT_WHATSAPP_URL", None),
        "hr_name": os.getenv("INPUT_HR_NAME", None),
        "language": os.getenv("INPUT_LANGUAGE", None),
        "is_return_visit": int(os.getenv("INPUT_IS_RETURN_VISIT", "0"))  # 注意类型转换
    }


    # --------------------------- 消息发送配置 ---------------------------
    SEND_MSG_URL = os.getenv(
        "SEND_MSG_URL", "https://pn3cs.rocketgo.vip/prod-api2/biz/chat/sendMsg"
    )

    # --------------------------- 数据库配置 ---------------------------
    # 使用用户数据目录作为数据库路径
    DB_PATH = os.getenv("DB_PATH", None)
    if DB_PATH and not os.path.isabs(DB_PATH):
        # 如果是相对路径，转换为用户数据目录下的绝对路径
        DB_PATH = str(USER_DATA_DIR / DB_PATH)
    elif not DB_PATH:
        # 默认使用用户数据目录
        DB_PATH = str(USER_DATA_DIR / "conversations.db")

    # --------------------------- 其他配置 ---------------------------
    # 验证码图片保存路径
    CAPTCHA_IMAGE_PATH = os.getenv("CAPTCHA_IMAGE_PATH", None)
    if CAPTCHA_IMAGE_PATH and not os.path.isabs(CAPTCHA_IMAGE_PATH):
        # 如果是相对路径，转换为用户数据目录下的绝对路径
        CAPTCHA_IMAGE_PATH = str(USER_DATA_DIR / CAPTCHA_IMAGE_PATH)
    elif not CAPTCHA_IMAGE_PATH:
        # 默认使用用户数据目录
        CAPTCHA_IMAGE_PATH = str(USER_DATA_DIR / "验证码.png")


    @classmethod
    def get_all_config(cls) -> dict:
        """获取所有配置项（用于调试）"""
        config_dict = {}
        for attr_name in dir(cls):
            if not attr_name.startswith('_') and not callable(getattr(cls, attr_name)):
                config_dict[attr_name] = getattr(cls, attr_name)
        return config_dict

    @classmethod
    def print_config(cls):
        """打印所有配置项"""
        print("=" * 50)
        print("当前配置:")
        print("=" * 50)
        for key, value in cls.get_all_config().items():
            # 隐藏敏感信息
            if any(sensitive in key.upper() for sensitive in ['PASSWORD', 'TOKEN', 'KEY']):
                display_value = '*' * len(str(value)) if value else 'None'
            else:
                display_value = value
            print(f"{key}: {display_value}")
        print("=" * 50)

# 创建全局配置实例
config = Config()

if __name__ == '__main__':
    # 打印所有参数查看是否使用环境变量
    config.print_config()
