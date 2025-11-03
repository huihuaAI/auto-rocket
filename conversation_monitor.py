#!/usr/bin/env python3
"""
对话监听服务 - 定期检查需要跟进的对话并主动发送消息
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any

from db_manager import ConversationManager
from dify_client import DifyChatBot

logger = logging.getLogger(__name__)


class ConversationMonitor:
    """对话监听服务

    功能：
    - 每5秒查询一次数据库
    - 找出更新时间超过3小时且激活次数<=10的对话
    - 调用Dify生成消息
    - 通过回调发送消息
    """

    def __init__(
        self,
        db_path: str = "conversations.db",
        dify_url: str = "",
        dify_api_key: str = "",
        dify_input_params: dict = None,
        cs_id: str = "",
        send_message_callback: Optional[Callable] = None,
        check_interval: int = 5,
        stale_hours: int = 3,
        max_active_count: int = 10
    ):
        """初始化监听服务

        Args:
            db_path: 数据库路径
            dify_url: Dify API地址
            dify_api_key: Dify API密钥
            dify_input_params: Dify输入参数
            send_message_callback: 发送消息的回调函数，签名为 async def callback(message_info, reply_content)
            check_interval: 检查间隔（秒）
            stale_hours: 距离上次更新的小时数阈值
            max_active_count: 最大主动激活次数
        """
        self.db_manager = ConversationManager(db_path)
        self.dify_url = dify_url
        self.dify_api_key = dify_api_key
        self.dify_input_params = dify_input_params or {}
        self.cs_id = cs_id
        self.send_message_callback = send_message_callback
        self.check_interval = check_interval
        self.stale_hours = stale_hours
        self.max_active_count = max_active_count

        self._running = False
        self._task: Optional[asyncio.Task] = None

        # 用于跟踪已处理的对话，避免重复发送
        self._processed_conversations = set()

    async def start(self):
        """启动监听服务"""
        if self._running:
            logger.warning("监听服务已在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"对话监听服务已启动 - 检查间隔: {self.check_interval}秒, 超时阈值: {self.stale_hours}小时, 最大激活次数: {self.max_active_count}")

    async def stop(self):
        """停止监听服务"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("对话监听服务已停止")

    async def _monitor_loop(self):
        """监听循环"""
        while self._running:
            try:
                await self._check_and_process_conversations()
            except Exception as e:
                logger.error(f"监听循环出错: {e}", exc_info=True)

            # 等待下一次检查
            await asyncio.sleep(self.check_interval)

    async def _check_and_process_conversations(self):
        """检查并处理需要跟进的对话"""
        # 查询需要跟进的对话
        stale_conversations = self.db_manager.get_stale_conversations(
            hours=self.stale_hours,
            max_active_count=self.max_active_count
        )

        if not stale_conversations:
            logger.debug("当前没有需要跟进的对话")
            return

        logger.info(f"发现 {len(stale_conversations)} 个需要跟进的对话")

        # 处理每个对话
        for conv in stale_conversations:
            try:
                # 检查是否已经处理过（避免在5秒内重复发送）
                chat_user_id = conv['chat_user_id']

                # 简单的去重机制：记录本轮检查已处理的对话
                if chat_user_id in self._processed_conversations:
                    logger.debug(f"对话 {chat_user_id} 已在本轮处理，跳过")
                    continue

                await self._process_single_conversation(conv)

                # 标记为已处理
                self._processed_conversations.add(chat_user_id)

            except Exception as e:
                logger.error(f"处理对话 {conv.get('chat_user_id')} 时出错: {e}", exc_info=True)

        # 清理已处理记录（定期清理，避免内存泄漏）
        if len(self._processed_conversations) > 1000:
            self._processed_conversations.clear()

    async def _process_single_conversation(self, conv: Dict[str, Any]):
        """处理单个对话

        Args:
            conv: 对话记录字典
        """
        chat_user_id = conv['chat_user_id']
        account_id = conv['account_id']
        friend_id = conv['friend_id']
        active_count = conv.get('active_count', 0)

        logger.info(f"准备跟进对话: chat_user_id={chat_user_id}, account={account_id}, friend={friend_id}, active_count={active_count}")

        try:
            # 创建Dify客户端
            chatbot = DifyChatBot(
                base_url=self.dify_url,
                api_key=self.dify_api_key,
                input_params=self.dify_input_params,
                db_path=self.db_manager.db_path
            )

            # 设置用户信息
            chatbot.set_user(chat_user_id, account_id, friend_id)

            # 调用Dify生成主动问候消息
            # 这里可以根据需求自定义问候语，或者让AI生成
            greeting_prompt = "system_return_visit"
            result = await chatbot.chat_completion(greeting_prompt, stream=False)

            reply_content = result.get("answer", "")

            if not reply_content:
                logger.warning(f"Dify返回空消息，跳过发送: chat_user_id={chat_user_id}")
                return

            logger.info(f"Dify生成的消息: {reply_content}")

            if reply_content == "END":
                logger.info("收到END信号，结束对话")
                # 收到END信号，增加主动激活次数，避免后续重复发送
                self.db_manager.increment_active_count(chat_user_id, increment=100)
                return reply_content

            # 增加激活次数
            self.db_manager.increment_active_count(chat_user_id)

            # 如果有发送消息的回调，调用它
            if self.send_message_callback:
                message_info = {
                    "cs_id": self.cs_id,
                    "cs_username": account_id,
                    "user_id": friend_id,
                    "chat_type": 1,
                    "cs_chat_user_id": chat_user_id
                }

                await self.send_message_callback(message_info, reply_content)
                logger.info(f"已主动发送消息到用户 {friend_id}: {reply_content}")
            else:
                logger.warning("未设置发送消息回调，无法发送消息")

        except Exception as e:
            logger.error(f"处理对话 {chat_user_id} 时出错: {e}", exc_info=True)

