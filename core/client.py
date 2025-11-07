import asyncio
import logging
from config import config
from typing import Any, Optional
import base64
from PIL import Image
from io import BytesIO
import aiohttp
import ddddocr
from core.auth_manager import AuthManager
from core.http_client import HttpClient

logger = logging.getLogger(__name__)


def base64_to_image(base64_str, output_path):
    """
    将Base64编码字符串转换为图片并保存

    参数:
        base64_str: Base64编码字符串
        output_path: 图片保存路径，如"output.png"
    """
    try:
        # 解码Base64数据
        image_data = base64.b64decode(base64_str)

        # 将字节数据转换为图片
        image = Image.open(BytesIO(image_data))

        # 保存图片
        image.save(output_path)
        print(f"图片已成功保存至: {output_path}")
        return True
    except Exception as e:
        print(f"转换失败: {str(e)}")
        return False


class Client:
    """RocketGo客户端 - 处理登录、用户信息、会话信息等。

    主要功能:
    - login() -> 登录并保存认证信息
    - get_user_info() -> 获取用户信息
    - get_session_info() -> 获取会话信息
    - send_message() -> 发送消息
    - set_read() -> 设置对话已读
    """

    def __init__(self, auth_manager: Optional[AuthManager] = None, http_client: Optional[HttpClient] = None) -> None:
        """初始化Client

        Args:
            auth_manager: 认证管理器，如果不提供则创建新实例
            http_client: HTTP客户端，如果不提供则创建新实例
        """
        self.auth_manager = auth_manager or AuthManager()
        self.http_client = http_client or HttpClient(self.auth_manager)

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """登录并保存 token（如果有）。返回登录响应的 json。"""
        # 尝试登录，给验证码识别错误最多 3 次机会
        sess = await self.auth_manager.get_session()
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            # 获取验证码图片并识别
            uuid, code = await self.captcha_image()
            payload = {
                "code": code,
                "googleAuthCode": "",
                "password": password,
                "username": username,
                "uuid": uuid,
            }
            logger.info("尝试登录 %s (attempt %d/%d)", config.rocketgo.login_url, attempt, max_attempts)
            async with sess.post(config.rocketgo.login_url, json=payload,
                                 timeout=aiohttp.ClientTimeout(total=20)) as resp:
                text = await resp.text()
                if resp.status != 200:
                    logger.error("登录失败 status=%s text=%s", resp.status, text)
                    raise aiohttp.ClientResponseError(
                        status=resp.status,
                        request_info=resp.request_info,
                        history=resp.history,
                    )
                data = await resp.json(content_type=None)

                # 如果返回 token，则登录成功
                token = data.get("token") or data.get("access_token")
                if token:
                    self.auth_manager.set_token(token)
                    # 把 token 写进默认 headers（根据后端要求可能是 Bearer）
                    sess.headers.update({"Authorization": f"Bearer {token}"})
                    logger.info("登录成功，token 已保存")
                    return data

                # 未返回 token，检查是否为验证码识别错误，如果是则重试
                msg = str(data.get("msg") or data.get("message") or "")
                msg_lower = msg.lower()
                # 判断是否为验证码相关的错误提示（兼容中英混合提示）
                is_captcha_error = any(
                    key in msg_lower
                    for key in (
                        "验证码",
                        "验证码错误",
                        "验证码不正确",
                        "用户不存在/密码错误",
                        "captcha",
                        "invalid code",
                        "incorrect code",
                        "code error",
                        "verification code",
                    )
                )

                if is_captcha_error and attempt < max_attempts:
                    logger.warning(
                        "验证码可能识别错误（%s），正在重试 (%d/%d)", msg or text, attempt, max_attempts
                    )
                    await asyncio.sleep(0.5)
                    continue

                # 不是验证码错误或已到最大尝试次数，返回响应（由调用方决定如何处理）
                if not is_captcha_error:
                    logger.info("登录响应未包含 token，可能为其他错误：%s", data)
                else:
                    logger.error("尝试次数用尽，登录失败：%s", data)
                return data
        # 理论上上面的循环会在所有分支返回；为了类型检查，在这里添加兜底返回空字典
        return {}

    async def get_user_info(self) -> None:
        """获取用户信息，返回 json。"""
        logger.info("请求用户信息 %s", config.rocketgo.user_info_url)
        data = await self.http_client.get(config.rocketgo.user_info_url)
        user_id = str(data["user"]["userId"])
        self.auth_manager.set_user_id(user_id)
        logger.debug("用户ID: %s", user_id)

    async def get_session_info(self) -> None:
        """获取会话信息，返回 json。"""
        logger.info("请求会话信息 %s", config.rocketgo.session_url)
        data = await self.http_client.get(config.rocketgo.session_url)
        token_id = data["csRow"]["tokenId"]
        self.auth_manager.set_token_id(token_id)
        logger.debug("会话信息TokenID: %s", token_id)

    async def send_message(self, message_info: dict[str, Any], reply_content: str) -> bool:
        """发送消息，返回是否发送成功。"""
        try:
            # 根据main.py中的注释构造发送消息的请求体
            payload = {
                "csId": message_info.get("cs_id"),
                "chatContent": reply_content,
                "csUsername": message_info.get("cs_username"),
                "username": message_info.get("user_id"),
                "isSend": 1,  # 表示发送消息
                "isRead": 1,  # 标记为已读
                "chatIndex": 1,  # 可以根据需要调整
                "chatType": message_info.get("chat_type", 1),
                "csChatUserId": message_info.get("cs_chat_user_id"),
                "isFakePkmsg": 0
            }

            logger.info(f"准备发送回复消息: {payload}")

            status, response_text = await self.http_client.post_raw_response(
                config.send.msg_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            )

            if status == 200:
                logger.info(f"消息发送成功: {response_text}")
                return True
            else:
                logger.error(f"消息发送失败: status={status}, response={response_text}")
                return False

        except Exception as e:
            logger.error(f"发送消息时发生错误: {e}")
            return False

    async def set_read(self, chat_id: str) -> None:
        """设置对话已读"""
        data = await self.http_client.post(config.rocketgo.set_read_url + chat_id)
        code = data["code"]
        msg = data["msg"]
        if code != 200:
            logger.error(f"设置对话已读失败，状态码: {code}，消息: {msg}")
            return
        logger.info(f"设置对话已读成功，对话ID: {chat_id}")

    async def captcha_image(self) -> tuple[str, Any]:
        """获取验证码图片。返回包含验证码图片 base64 编码和 uuid 的元组。"""
        sess = await self.auth_manager.get_session()
        async with sess.get(config.rocketgo.captcha_image_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取验证码图片失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            code = data["code"]
        if code != 200:
            logger.error("获取验证码失败 code=%s", code)
            raise aiohttp.ClientResponseError(
                status=resp.status, request_info=resp.request_info, history=resp.history
            )
        uuid = data["uuid"]
        img = data["img"]
        # 保存验证码base64图片
        base64_to_image(img, config.other.captcha_image_path)
        ocr = ddddocr.DdddOcr()
        # 读取验证码图片
        image = open(config.other.captcha_image_path, "rb").read()
        result = ocr.classification(image)
        logger.info("验证码识别结果: %s", result)
        return uuid, result
