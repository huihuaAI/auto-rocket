"""
认证管理器 - 负责管理认证token和session
"""
import aiohttp
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """认证管理器 - 单一职责：管理认证状态"""

    def __init__(self) -> None:
        self._auth_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._token_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def set_token(self, token: str) -> None:
        """设置认证token"""
        self._auth_token = token
        logger.debug(f"Token已更新")

    def get_token(self) -> Optional[str]:
        """获取认证token"""
        return self._auth_token

    def set_user_id(self, user_id: str) -> None:
        """设置用户ID"""
        self._user_id = user_id

    def get_user_id(self) -> Optional[str]:
        """获取用户ID"""
        return self._user_id

    def set_token_id(self, token_id: str) -> None:
        """设置token ID"""
        self._token_id = token_id

    def get_token_id(self) -> Optional[str]:
        """获取token ID"""
        return self._token_id

    async def get_auth_headers(self) -> dict[str, str]:
        """获取带认证的headers"""
        headers = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    async def close(self) -> None:
        """关闭session"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("Session已关闭")