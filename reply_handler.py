#!/usr/bin/env python3
"""
消息发送模块 - 发送回复消息到原平台
"""

import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MessageSender:
    """消息发送器 - 发送回复到原平台"""

    def __init__(self, send_url: str, auth_token: str):
        self.send_url = send_url
        self.auth_token = auth_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """确保session存在"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """关闭session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_reply_message(self, message_info: Dict[str, Any], reply_content: str) -> bool:
        """发送回复消息"""
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

            session = await self._ensure_session()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}"
            }

            async with session.post(
                self.send_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_text = await response.text()

                if response.status == 200:
                    logger.info(f"消息发送成功: {response_text}")
                    return True
                else:
                    logger.error(f"消息发送失败: status={response.status}, response={response_text}")
                    return False

        except Exception as e:
            logger.error(f"发送消息时发生错误: {e}")
            return False

class IntegratedMessageHandler:
    """集成的消息处理器 - 整合监听、处理、回复的完整流程"""

    def __init__(self,
                 dify_url: str,
                 dify_api_key: str,
                 input_params:dict,
                 send_url: str,
                 auth_token: str,
                 client=None):
        # 导入消息处理器
        from chat_processor import MessageProcessor

        # 创建消息发送器
        self.message_sender = MessageSender(send_url, auth_token)

        # 创建消息处理器，并传入发送回调和client实例
        self.message_processor = MessageProcessor(
            dify_url=dify_url,
            dify_api_key=dify_api_key,
            input_params=input_params,
            send_message_callback=self.send_message_callback,
            client=client  # 传入client实例用于调用set_read
        )

    async def send_message_callback(self, message_info: Dict[str, Any], reply_content: str):
        """发送消息的回调函数"""
        success = await self.message_sender.send_reply_message(message_info, reply_content)
        if success:
            logger.info(f"成功回复用户 {message_info['user_id']}: {reply_content}")
        else:
            logger.error(f"回复用户 {message_info['user_id']} 失败")

    async def handle_websocket_message(self, raw_message: str):
        """处理WebSocket消息的主函数"""
        await self.message_processor.process_message(raw_message)


    async def close(self):
        """关闭资源"""
        await self.message_sender.close()