#!/usr/bin/env python3
"""
RocketGo服务层 - 整合Client、WebSocket和消息处理功能
提供统一的服务接口，降低耦合度
"""

import asyncio
import logging
from typing import Optional, Callable
from enum import Enum

from core.auth_manager import AuthManager
from core.http_client import HttpClient
from core.client import Client
from core.ws import WSClient
from core.chat_processor import MessageProcessor
from core.conversation_monitor import ConversationMonitor
from config import config

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态枚举"""
    STOPPED = "停止"
    STARTING = "启动中"
    RUNNING = "运行中"
    STOPPING = "停止中"
    ERROR = "错误"


class RocketService:
    """RocketGo服务 - 统一管理所有业务逻辑

    功能：
    - 用户登录和认证
    - WebSocket连接管理
    - 消息接收和处理
    - 对话监听服务
    """

    def __init__(self,
                 on_status_change: Optional[Callable[[ServiceStatus], None]] = None,
                 on_message_received: Optional[Callable[[str], None]] = None):
        """初始化服务

        Args:
            on_status_change: 状态变化回调
            on_message_received: 收到消息的回调
        """
        # 认证层
        self.auth_manager = AuthManager()
        self.http_client = HttpClient(self.auth_manager)
        self.client = Client(self.auth_manager, self.http_client)

        # WebSocket客户端
        self.ws_client: Optional[WSClient] = None

        # 对话监听服务
        self.conversation_monitor: Optional[ConversationMonitor] = None

        # 服务状态
        self._status = ServiceStatus.STOPPED
        self._ws_task: Optional[asyncio.Task] = None

        # 回调函数
        self.on_status_change = on_status_change
        self.on_message_received = on_message_received

        # 保存登录凭据，用于重启时重新登录
        self._username: Optional[str] = None
        self._password: Optional[str] = None

    @property
    def status(self) -> ServiceStatus:
        """获取服务状态"""
        return self._status

    def _set_status(self, status: ServiceStatus):
        """设置服务状态并触发回调"""
        self._status = status
        logger.info(f"服务状态变更: {status.value}")
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception as e:
                logger.error(f"状态变化回调出错: {e}")

    async def login(self, username: str, password: str) -> bool:
        """登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            是否登录成功
        """
        try:
            logger.info(f"开始登录，用户名: {username}")

            # 调用Client的login方法
            result = await self.client.login(username, password)

            # 检查是否返回token
            token = result.get("token") or result.get("access_token")
            if not token:
                logger.error(f"登录失败: {result.get('msg') or result.get('message') or '未返回token'}")
                return False

            # 获取用户信息和会话信息
            await self.client.get_user_info()
            await self.client.get_session_info()

            # 保存登录凭据，用于重启时重新登录
            self._username = username
            self._password = password

            logger.info("登录成功，已获取用户信息和会话信息")
            return True

        except Exception as e:
            logger.error(f"登录过程出错: {e}", exc_info=True)
            return False

    async def start(self):
        """启动服务 - 连接WebSocket"""
        if self._status in [ServiceStatus.STARTING, ServiceStatus.RUNNING]:
            logger.warning("服务已在运行中")
            return

        try:
            self._set_status(ServiceStatus.STARTING)

            # 检查是否已登录
            token_id = self.auth_manager.get_token_id()
            if not token_id:
                raise RuntimeError("未登录，无法启动服务")

            # 创建消息处理器
            message_processor = MessageProcessor(
                dify_url=config.dify.url,
                dify_api_key=config.dify.api_key,
                input_params=dict(config.dify.input),
                message_service=self.client,  # Client实现了MessageServiceProtocol
                db_path=config.db.path
            )

            # 定义消息处理回调
            async def handle_message(raw: str):
                """处理接收到的消息"""
                # 触发消息接收回调
                if self.on_message_received:
                    try:
                        self.on_message_received(raw)
                    except Exception as e:
                        logger.error(f"消息接收回调出错: {e}")

                # 处理消息
                try:
                    await message_processor.process_message(raw)
                except Exception as e:
                    logger.error(f"消息处理出错: {e}", exc_info=True)

            # 定义认证错误处理回调
            async def handle_auth_error():
                """处理认证错误，尝试重新登录"""
                if not self._username or not self._password:
                    logger.error("无法重新登录：缺少保存的用户名或密码")
                    return None
                
                logger.info(f"尝试使用保存的凭据重新登录: {self._username}")
                success = await self.login(self._username, self._password)
                
                if success:
                    new_token = self.auth_manager.get_token_id()
                    logger.info("重新登录成功，返回新token")
                    return new_token
                else:
                    logger.error("重新登录失败")
                    return None

            # 创建WebSocket客户端并注入消息处理回调
            self.ws_client = WSClient(
                token_id, 
                message_handler=handle_message,
                on_auth_error=handle_auth_error
            )

            # 启动WebSocket连接（在后台运行）
            self._ws_task = asyncio.create_task(self.ws_client.connect())

            self._set_status(ServiceStatus.RUNNING)
            logger.info("服务启动成功")

        except Exception as e:
            logger.error(f"启动服务失败: {e}", exc_info=True)
            self._set_status(ServiceStatus.ERROR)
            raise

    async def stop(self):
        """停止服务"""
        if self._status == ServiceStatus.STOPPED:
            logger.warning("服务已停止")
            return

        try:
            self._set_status(ServiceStatus.STOPPING)

            # 停止对话监听服务
            if self.conversation_monitor:
                await self.conversation_monitor.stop()
                self.conversation_monitor = None

            # 取消WebSocket任务
            if self._ws_task and not self._ws_task.done():
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except asyncio.CancelledError:
                    pass
                self._ws_task = None

            self.ws_client = None

            self._set_status(ServiceStatus.STOPPED)
            logger.info("服务已停止")

        except Exception as e:
            logger.error(f"停止服务失败: {e}", exc_info=True)
            self._set_status(ServiceStatus.ERROR)
            raise

    async def start_conversation_monitor(self,
                                         check_interval: int = 5,
                                         stale_hours: int = 3,
                                         max_active_count: int = 3):
        """启动对话监听服务

        Args:
            check_interval: 检查间隔（秒）
            stale_hours: 距离上次更新的小时数阈值
            max_active_count: 最大主动激活次数
        """
        if self.conversation_monitor:
            logger.warning("对话监听服务已在运行")
            return

        try:
            # 获取csId
            cs_id = self.auth_manager.get_token_id()
            if not cs_id:
                raise RuntimeError("未获取到csId，无法启动对话监听服务")

            # 创建对话监听服务
            self.conversation_monitor = ConversationMonitor(
                db_path=config.db.path,
                dify_url=config.dify.url,
                dify_api_key=config.dify.api_key,
                dify_input_params=dict(config.dify.input),
                cs_id=cs_id,
                send_message_callback=self.client.send_message,
                check_interval=check_interval,
                stale_hours=stale_hours,
                max_active_count=max_active_count
            )

            await self.conversation_monitor.start()
            logger.info("对话监听服务已启动")

        except Exception as e:
            logger.error(f"启动对话监听服务失败: {e}", exc_info=True)
            raise

    async def stop_conversation_monitor(self):
        """停止对话监听服务"""
        if not self.conversation_monitor:
            logger.warning("对话监听服务未运行")
            return

        try:
            await self.conversation_monitor.stop()
            self.conversation_monitor = None
            logger.info("对话监听服务已停止")
        except Exception as e:
            logger.error(f"停止对话监听服务失败: {e}", exc_info=True)
            raise

    async def restart(self, full_restart: bool = True):
        """重启服务

        Args:
            full_restart: 是否执行完整重启（重新登录、获取用户信息和会话信息）。
                         默认为True。如果为False，则只重启WebSocket连接。
        """
        logger.info(f"重启服务... (完整重启: {full_restart})")

        # 停止服务
        await self.stop()
        await asyncio.sleep(1)  # 等待资源释放

        # 如果是完整重启，且有保存的登录凭据，则重新登录
        if full_restart and self._username and self._password:
            logger.info("执行完整重启：重新登录并获取用户信息、会话信息...")
            success = await self.login(self._username, self._password)
            if not success:
                logger.error("完整重启失败：重新登录失败")
                raise RuntimeError("重新登录失败")

        # 启动服务
        await self.start()

    async def cleanup(self):
        """清理资源"""
        try:
            await self.stop()
            await self.auth_manager.close()
        except Exception as e:
            logger.error(f"清理资源失败: {e}", exc_info=True)

    def is_running(self) -> bool:
        """判断服务是否正在运行"""
        return self._status == ServiceStatus.RUNNING

    def is_logged_in(self) -> bool:
        """判断是否已登录"""
        return self.auth_manager.get_token() is not None
