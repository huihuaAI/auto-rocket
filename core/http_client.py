"""
HTTP客户端 - 负责HTTP请求的底层实现
"""
import aiohttp
import logging
from typing import Any, Optional
from core.auth_manager import AuthManager

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP客户端 - 封装HTTP请求，支持认证"""

    def __init__(self, auth_manager: AuthManager) -> None:
        self.auth_manager = auth_manager

    async def get(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        **kwargs
    ) -> dict[str, Any]:
        """发送GET请求"""
        session = await self.auth_manager.get_session()

        # 合并认证headers
        auth_headers = await self.auth_manager.get_auth_headers()
        if headers:
            auth_headers.update(headers)

        logger.info(f"GET {url}")
        async with session.get(url, headers=auth_headers, timeout=timeout or aiohttp.ClientTimeout(total=20), **kwargs) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error(f"GET请求失败 status={resp.status} text={text}")
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            return await resp.json(content_type=None)

    async def post(
        self,
        url: str,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        **kwargs
    ) -> dict[str, Any]:
        """发送POST请求"""
        session = await self.auth_manager.get_session()

        # 合并认证headers
        auth_headers = await self.auth_manager.get_auth_headers()
        if headers:
            auth_headers.update(headers)

        logger.info(f"POST {url}")
        async with session.post(url, json=json, headers=auth_headers, timeout=timeout or aiohttp.ClientTimeout(total=20), **kwargs) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error(f"POST请求失败 status={resp.status} text={text}")
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            return await resp.json(content_type=None)

    async def post_raw_response(
        self,
        url: str,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        **kwargs
    ) -> tuple[int, str]:
        """发送POST请求，返回原始响应（status code和text）"""
        session = await self.auth_manager.get_session()

        # 合并认证headers
        auth_headers = await self.auth_manager.get_auth_headers()
        if headers:
            auth_headers.update(headers)

        logger.info(f"POST {url}")
        async with session.post(url, json=json, headers=auth_headers, timeout=timeout or aiohttp.ClientTimeout(total=20), **kwargs) as resp:
            text = await resp.text()
            return resp.status, text