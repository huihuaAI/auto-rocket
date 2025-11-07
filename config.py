#!/usr/bin/env python3
"""
配置文件 - 集中管理所有配置项
"""

import os
from dotenv import load_dotenv
# 加载 .env 文件
load_dotenv()


class Config:
    """应用配置类"""

    # --------------------------- 基础配置 ---------------------------
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_FILE = os.getenv("LOG_FILE", "auto_reply.log")

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
    DB_PATH = os.getenv("DB_PATH", "conversations.db")

    # --------------------------- 其他配置 ---------------------------
    # 验证码图片保存路径
    CAPTCHA_IMAGE_PATH = os.getenv("CAPTCHA_IMAGE_PATH", "验证码.png")


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