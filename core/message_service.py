"""
消息服务接口 - 定义消息发送和设置已读的抽象
"""
from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class MessageServiceProtocol(Protocol):
    """消息服务接口 - 定义消息相关操作的抽象"""

    async def send_message(self, message_info: dict[str, Any], reply_content: str) -> bool:
        """发送消息

        Args:
            message_info: 消息信息字典
            reply_content: 回复内容

        Returns:
            bool: 是否发送成功
        """
        ...

    async def set_read(self, chat_id: str) -> None:
        """设置对话已读

        Args:
            chat_id: 对话ID
        """
        ...
