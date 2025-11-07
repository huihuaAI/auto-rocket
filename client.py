#!/usr/bin/env python3
"""
RocketGo客户端模块 - 处理登录、WebSocket连接和自动回复
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
import ddddocr

from 验证码识别 import base64_to_image
from reply_handler import IntegratedMessageHandler
from config import Config
from playwright_ws import PlaywrightWSClient
from conversation_monitor import ConversationMonitor

logger = logging.getLogger(__name__)

class RocketGoClient:
    """RocketGo客户端 - 处理登录、WebSocket连接和自动回复

    主要功能:
    - login() -> 登录并保存认证信息
    - get_user_info() -> 获取用户信息
    - get_session_info() -> 获取会话信息
    - start_auto_reply() -> 启动自动回复监听
    """

    def __init__(self) -> None:
        # 我们在一个 session 中保存 cookie 和 headers
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._token_id: Optional[str] = None

        # 自动回复处理器
        self.message_handler: Optional[IntegratedMessageHandler] = None

        # Playwright WebSocket客户端
        self.ws_client: Optional[PlaywrightWSClient] = None

        # 对话监听服务
        self.conversation_monitor: Optional[ConversationMonitor] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def captcha_image(self) -> tuple[str, Any]:
        """获取验证码图片。返回包含验证码图片 base64 编码和 uuid 的元组。"""
        sess = await self._ensure_session()
        async with sess.get(Config.CAPTCHA_IMAGE_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
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
        base64_to_image(img, Config.CAPTCHA_IMAGE_PATH)
        ocr = ddddocr.DdddOcr()
        # 读取验证码图片
        image = open(Config.CAPTCHA_IMAGE_PATH, "rb").read()
        result = ocr.classification(image)
        logger.info("验证码识别结果: %s", result)
        return uuid, result

    async def login(
        self, username: str = Config.USERNAME, password: str = Config.PASSWORD
    ) -> Dict[str, Any]:
        """登录并保存 token（如果有）。返回登录响应的 json。"""
        # 尝试登录，给验证码识别错误最多 3 次机会
        sess = await self._ensure_session()
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
            logger.info("尝试登录 %s (attempt %d/%d)", Config.LOGIN_URL, attempt, max_attempts)
            async with sess.post(Config.LOGIN_URL, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                text = await resp.text()
                if resp.status != 200:
                    logger.error("登录失败 status=%s text=%s", resp.status, text)
                    raise aiohttp.ClientResponseError(
                        status=resp.status,
                        request_info=resp.request_info,
                        history=resp.history,
                    )
                data = await resp.json(content_type=None)
                print(data)

                # 如果返回 token，则登录成功
                token = data.get("token") or data.get("access_token")
                if token:
                    self._auth_token = token
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
        sess = await self._ensure_session()
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        logger.info("请求用户信息 %s", Config.USER_INFO_URL)
        async with sess.get(Config.USER_INFO_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取用户信息失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            self._user_id = str(data["user"]["userId"])
            logger.debug("用户ID: %s", self._user_id)


    async def get_session_info(self) -> None:
        """获取会话信息，返回 json。"""
        sess = await self._ensure_session()
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        logger.info("请求会话信息 %s", Config.SESSION_URL)
        async with sess.get(Config.SESSION_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取会话信息失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            self._token_id = data["csRow"]["tokenId"]
            logger.debug("会话信息TokenID: %s", self._token_id)


    async def get_not_read_message_count(self) -> int:
        """获取未读消息数量"""
        sess = await self._ensure_session()
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        logger.info("请求未读消息数量 %s", Config.NOT_READ_MESSAGE_URL)
        async with sess.get(Config.NOT_READ_MESSAGE_URL, params={"csId": self._user_id}, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取未读消息数量失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            print(data)
            not_read_message_count = data["notReadNum"]
            logger.info("未读消息数量: %s", not_read_message_count)
            return not_read_message_count

    async def get_account_info(self) -> None:
        """获取账号信息，返回 json。"""
        sess = await self._ensure_session()
        logger.info("请求账号信息 %s", Config.ACCOUNT_INFO_URL)
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        params = {
            "csId": self._user_id,
            "logged": "1",
            "pushName": Config.USERNAME,
            "accountType": "0",
            "pageSize": "100",
            "pageNum": "1"
        }
        async with sess.get(Config.ACCOUNT_INFO_URL, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取账号信息失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            """
            {
              "total": 4,
              "rows": [
                {
                  "createBy": null,
                  "createTime": null,
                  "updateBy": null,
                  "updateTime": null,
                  "remark": "",
                  "username": "6011757555174756",
                  "createDate": null,
                  "cc": null,
                  "number": null,
                  "language": null,
                  "country": null,
                  "appType": null,
                  "deviceInfo": null,
                  "pushName": "Mia",
                  "status": 1,
                  "working": null,
                  "updateDate": null,
                  "blockReason": null,
                  "blockDate": null,
                  "blockIp": null,
                  "failedReason": null,
                  "mcc": null,
                  "mnc": null,
                  "socksHost": null,
                  "socksPort": null,
                  "socksUsername": null,
                  "socksPassword": null,
                  "loginDate": null,
                  "logging": null,
                  "picturePreview": null,
                  "data": null,
                  "groupId": null,
                  "type": null,
                  "business": null,
                  "about": null,
                  "setAboutTime": null,
                  "userPrivacyStrategy": null,
                  "authPrivateKey": null,
                  "identityPrivateKey": null,
                  "maxPreKey": null,
                  "maxSentPreKey": null,
                  "finishProduct": null,
                  "registerDate": null,
                  "session": null,
                  "login": 601175755517,
                  "workingServer": null,
                  "countrySel": null,
                  "countryId": null,
                  "ipType": null,
                  "ipGroupId": null,
                  "csId": null,
                  "createId": null,
                  "accountType": null,
                  "ipId": null,
                  "keyword4": null,
                  "csName": null,
                  "isCs": null,
                  "readNum": 17,
                  "groupReadCount": 0,
                  "avatarUrl": "http://rocketgo03new.oss-ap-southeast-1.aliyuncs.com/assets/video/feedback/20250920/c5142585105737cf28d53199861eccade1dba919.jpg",
                  "groupName": null,
                  "accountGroupId": null,
                  "logged": null,
                  "platform": null,
                  "sessionStr": null,
                  "accountStatus": null,
                  "configId": null,
                  "isSm": null,
                  "isPin": null,
                  "pinCode": null,
                  "executeDate": null,
                  "sendCount": null,
                  "friendsCount": null,
                  "isNotCs": null,
                  "keyword": null,
                  "limit": null,
                  "keepOnline": null,
                  "isList": null,
                  "ids": null,
                  "isAll": null,
                  "chargeName": null,
                  "sysUsername": null,
                  "ipStr": null,
                  "isHaveAvatar": null,
                  "isUpdateAvatar": null,
                  "csIds": null,
                  "moveStatus": null,
                  "isTop": 0,
                  "orderSort": null,
                  "symbol": null,
                  "isChatAi": null,
                  "chatLogTableName": "chat_log",
                  "friendsTableName": "friends"
                },
                {
                  "createBy": null,
                  "createTime": null,
                  "updateBy": null,
                  "updateTime": null,
                  "remark": "",
                  "username": "6011686526004528",
                  "createDate": null,
                  "cc": null,
                  "number": null,
                  "language": null,
                  "country": null,
                  "appType": null,
                  "deviceInfo": null,
                  "pushName": "Mia",
                  "status": 1,
                  "working": null,
                  "updateDate": null,
                  "blockReason": null,
                  "blockDate": null,
                  "blockIp": null,
                  "failedReason": null,
                  "mcc": null,
                  "mnc": null,
                  "socksHost": null,
                  "socksPort": null,
                  "socksUsername": null,
                  "socksPassword": null,
                  "loginDate": null,
                  "logging": null,
                  "picturePreview": null,
                  "data": null,
                  "groupId": null,
                  "type": null,
                  "business": null,
                  "about": null,
                  "setAboutTime": null,
                  "userPrivacyStrategy": null,
                  "authPrivateKey": null,
                  "identityPrivateKey": null,
                  "maxPreKey": null,
                  "maxSentPreKey": null,
                  "finishProduct": null,
                  "registerDate": null,
                  "session": null,
                  "login": 601168652600,
                  "workingServer": null,
                  "countrySel": null,
                  "countryId": null,
                  "ipType": null,
                  "ipGroupId": null,
                  "csId": null,
                  "createId": null,
                  "accountType": null,
                  "ipId": null,
                  "keyword4": null,
                  "csName": null,
                  "isCs": null,
                  "readNum": 3,
                  "groupReadCount": 0,
                  "avatarUrl": "http://rocketgo03new.oss-ap-southeast-1.aliyuncs.com/assets/video/feedback/20250920/4ed9ef2bcef2fa5a9d996cfecd4f9fd2da440cea.jpg",
                  "groupName": null,
                  "accountGroupId": null,
                  "logged": null,
                  "platform": null,
                  "sessionStr": null,
                  "accountStatus": null,
                  "configId": null,
                  "isSm": null,
                  "isPin": null,
                  "pinCode": null,
                  "executeDate": null,
                  "sendCount": null,
                  "friendsCount": null,
                  "isNotCs": null,
                  "keyword": null,
                  "limit": null,
                  "keepOnline": null,
                  "isList": null,
                  "ids": null,
                  "isAll": null,
                  "chargeName": null,
                  "sysUsername": null,
                  "ipStr": null,
                  "isHaveAvatar": null,
                  "isUpdateAvatar": null,
                  "csIds": null,
                  "moveStatus": null,
                  "isTop": 0,
                  "orderSort": null,
                  "symbol": null,
                  "isChatAi": null,
                  "chatLogTableName": "chat_log",
                  "friendsTableName": "friends"
                },
                {
                  "createBy": null,
                  "createTime": null,
                  "updateBy": null,
                  "updateTime": null,
                  "remark": "",
                  "username": "6011651879725128",
                  "createDate": null,
                  "cc": null,
                  "number": null,
                  "language": null,
                  "country": null,
                  "appType": null,
                  "deviceInfo": null,
                  "pushName": "Mia",
                  "status": 1,
                  "working": null,
                  "updateDate": null,
                  "blockReason": null,
                  "blockDate": null,
                  "blockIp": null,
                  "failedReason": null,
                  "mcc": null,
                  "mnc": null,
                  "socksHost": null,
                  "socksPort": null,
                  "socksUsername": null,
                  "socksPassword": null,
                  "loginDate": null,
                  "logging": null,
                  "picturePreview": null,
                  "data": null,
                  "groupId": null,
                  "type": null,
                  "business": null,
                  "about": null,
                  "setAboutTime": null,
                  "userPrivacyStrategy": null,
                  "authPrivateKey": null,
                  "identityPrivateKey": null,
                  "maxPreKey": null,
                  "maxSentPreKey": null,
                  "finishProduct": null,
                  "registerDate": null,
                  "session": null,
                  "login": 601165187972,
                  "workingServer": null,
                  "countrySel": null,
                  "countryId": null,
                  "ipType": null,
                  "ipGroupId": null,
                  "csId": null,
                  "createId": null,
                  "accountType": null,
                  "ipId": null,
                  "keyword4": null,
                  "csName": null,
                  "isCs": null,
                  "readNum": 1,
                  "groupReadCount": 0,
                  "avatarUrl": "http://rocketgo03new.oss-ap-southeast-1.aliyuncs.com/assets/video/feedback/20250920/4048bc6db2983b696090f0f402b95bc935a0563e.jpg",
                  "groupName": null,
                  "accountGroupId": null,
                  "logged": null,
                  "platform": null,
                  "sessionStr": null,
                  "accountStatus": null,
                  "configId": null,
                  "isSm": null,
                  "isPin": null,
                  "pinCode": null,
                  "executeDate": null,
                  "sendCount": null,
                  "friendsCount": null,
                  "isNotCs": null,
                  "keyword": null,
                  "limit": null,
                  "keepOnline": null,
                  "isList": null,
                  "ids": null,
                  "isAll": null,
                  "chargeName": null,
                  "sysUsername": null,
                  "ipStr": null,
                  "isHaveAvatar": null,
                  "isUpdateAvatar": null,
                  "csIds": null,
                  "moveStatus": null,
                  "isTop": 0,
                  "orderSort": null,
                  "symbol": null,
                  "isChatAi": null,
                  "chatLogTableName": "chat_log",
                  "friendsTableName": "friends"
                },
                {
                  "createBy": null,
                  "createTime": null,
                  "updateBy": null,
                  "updateTime": null,
                  "remark": "",
                  "username": "6011643773282047",
                  "createDate": null,
                  "cc": null,
                  "number": null,
                  "language": null,
                  "country": null,
                  "appType": null,
                  "deviceInfo": null,
                  "pushName": "Mia",
                  "status": 1,
                  "working": null,
                  "updateDate": null,
                  "blockReason": null,
                  "blockDate": null,
                  "blockIp": null,
                  "failedReason": null,
                  "mcc": null,
                  "mnc": null,
                  "socksHost": null,
                  "socksPort": null,
                  "socksUsername": null,
                  "socksPassword": null,
                  "loginDate": null,
                  "logging": null,
                  "picturePreview": null,
                  "data": null,
                  "groupId": null,
                  "type": null,
                  "business": null,
                  "about": null,
                  "setAboutTime": null,
                  "userPrivacyStrategy": null,
                  "authPrivateKey": null,
                  "identityPrivateKey": null,
                  "maxPreKey": null,
                  "maxSentPreKey": null,
                  "finishProduct": null,
                  "registerDate": null,
                  "session": null,
                  "login": 601164377328,
                  "workingServer": null,
                  "countrySel": null,
                  "countryId": null,
                  "ipType": null,
                  "ipGroupId": null,
                  "csId": null,
                  "createId": null,
                  "accountType": null,
                  "ipId": null,
                  "keyword4": null,
                  "csName": null,
                  "isCs": null,
                  "readNum": 0,
                  "groupReadCount": 0,
                  "avatarUrl": "http://rocketgo03new.oss-ap-southeast-1.aliyuncs.com/assets/video/feedback/20250920/4ed9ef2bcef2fa5a9d996cfecd4f9fd2da440cea.jpg",
                  "groupName": null,
                  "accountGroupId": null,
                  "logged": null,
                  "platform": null,
                  "sessionStr": null,
                  "accountStatus": null,
                  "configId": null,
                  "isSm": null,
                  "isPin": null,
                  "pinCode": null,
                  "executeDate": null,
                  "sendCount": null,
                  "friendsCount": null,
                  "isNotCs": null,
                  "keyword": null,
                  "limit": null,
                  "keepOnline": null,
                  "isList": null,
                  "ids": null,
                  "isAll": null,
                  "chargeName": null,
                  "sysUsername": null,
                  "ipStr": null,
                  "isHaveAvatar": null,
                  "isUpdateAvatar": null,
                  "csIds": null,
                  "moveStatus": null,
                  "isTop": 0,
                  "orderSort": null,
                  "symbol": null,
                  "isChatAi": null,
                  "chatLogTableName": "chat_log",
                  "friendsTableName": "friends"
                }
              ],
              "code": 200,
              "msg": "查询成功"
            }"""
            # 打印每一个账号下的未读消息数量
            account_list = data["accountList"]
            total = account_list["total"]
            code = account_list["code"]
            msg = account_list["msg"]
            if code != 200:
                logger.error(f"查询账号信息失败，状态码: {code}，消息: {msg}")
                return
            logger.info(f"账号{Config.USERNAME}查询到 {total} 个whatsapp账号")
            rows = account_list["rows"]
            for account in rows:
                # 未读数量
                read_num = account["readNum"]
                logger.info(f"账号 {account['pushName']} 未读消息数量: {read_num}")
                if read_num <= 0:
                    logger.info(f"账号 {account['pushName']} 未读消息数量为0，无需获取")
                    continue
                await self.get_friend_list(account["pushName"], account["username"])

    async def get_friend_list(self, account_name: str, cs_username: str):
        """获取好友列表"""
        sess = await self._ensure_session()
        logger.info(f"账号: {account_name} 请求好友列表 {Config.FRIENDS_URL} ")
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        params = {
            "csUsername": cs_username,
            "pageNum": 1,
            "pageSize": 100,
        }
        async with sess.get(Config.FRIENDS_URL, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取账号信息失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            chat_info = data["chatInfo"]
            chat_users = chat_info["chatUsers"]
            total = chat_users["total"]
            code = chat_users["code"]
            msg = chat_users["msg"]
            rows = chat_users["rows"]
            if code != 200:
                logger.error(f"查询好友列表失败，状态码: {code}，消息: {msg}")
                return
            logger.info(f"账号{account_name}查询到 {total} 个好友")
            for account in rows:
                remark_name = account["remarkName"]
                username = account["username"]
                chat_user_id = account["id"]
                # 未读数量
                read_num = account["readNum"]
                logger.info(f"好友 {account['remarkName']} 未读消息数量: {read_num}")
                if read_num <= 0:
                    logger.info(f"好友 {remark_name} 未读消息数量为0，无需获取")
                    continue
                await self.get_friend_chat(remark_name, username, chat_user_id, cs_username, read_num)

    async def get_friend_chat(self, remark_name: str, username: str, chat_user_id: str, cs_username: str, read_num: int):
        """获取好友聊天记录并自动回复未读消息"""
        sess = await self._ensure_session()
        logger.info(f"请求好友{remark_name}聊天记录 {Config.FRIENDS_CHAT_URL} ")
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        params = {
            "csUsername": cs_username,
            "username": username,
            "remarkName": remark_name,
            "chatUserId": chat_user_id,
            "isCs": 1,
            "pageNum": 1,
            "pageSize": read_num,
        }
        async with sess.get(Config.FRIENDS_CHAT_URL, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("获取好友聊天记录失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            total = data["total"]
            code = data["code"]
            msg = data["msg"]
            rows = data["rows"]
            if code != 200:
                logger.error(f"查询好友聊天记录失败，状态码: {code}，消息: {msg}")
                return
            logger.info(f"查询好友{remark_name}聊天记录成功，共 {total} 条")

            # 处理未读消息：只处理对方发送的消息（isSend == 0）
            for record in rows:
                # isSend 1 是我们发的，0 对方发的
                if record["isSend"] == 1:
                    logger.info(f"账号 {record['username']} 发送的消息: {record['chatContent']}")
                else:
                    logger.info(f"好友 {record['notify']}({record['username']}) 发送的消息: {record['chatContent']}")
                    # 如果有消息处理器，则处理这条未读消息
                    if self.message_handler:
                        await self._process_historical_message(record, cs_username, chat_user_id)

    async def _process_historical_message(self, record: Dict[str, Any], cs_username: str, chat_user_id: str):
        """处理历史未读消息 - 将历史消息转换为WebSocket格式并复用现有处理逻辑"""
        try:
            # 将历史消息转换为WebSocket消息格式（模拟sendType=2的格式）
            simulated_ws_message = {
                "sendType": 2,  # 异常响应，表示用户消息
                "sendInfo": {
                    "username": record.get("username", ""),  # 用户ID
                    "chatContent": record.get("chatContent", ""),  # 消息内容
                    "csUsername": cs_username,  # 客服账号
                    "csId": record.get("csId", self._user_id),  # 客服ID
                    "csChatUserId": chat_user_id,  # 对话用户ID
                    "isSend": 0,  # 0表示对方发送的
                    "login": record.get("login", ""),
                    "messageId": record.get("messageId", ""),
                    "id": record.get("id", ""),  # 用于标记已读
                }
            }

            # 转换为JSON字符串
            ws_message_str = json.dumps(simulated_ws_message, ensure_ascii=False)

            # 复用现有的消息处理逻辑
            logger.info(f"正在处理历史未读消息: {record.get('chatContent', '')[:50]}...")
            await self.message_handler.handle_websocket_message(ws_message_str)

        except Exception as e:
            logger.error(f"处理历史消息时出错: {e}")

    async def set_read(self, chat_id: str):
        """设置对话已读"""
        sess = await self._ensure_session()
        headers = {}
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
        async with sess.post(Config.SET_READ_URL + chat_id, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("设置对话已读失败 status=%s text=%s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    status=resp.status,
                    request_info=resp.request_info,
                    history=resp.history,
                )
            data = await resp.json(content_type=None)
            code = data["code"]
            msg = data["msg"]
            if code != 200:
                logger.error(f"设置对话已读失败，状态码: {code}，消息: {msg}")
                return
            logger.info(f"设置对话已读成功，对话ID: {chat_id}")

    async def start_websocket_monitoring(self):
        """启动WebSocket监听（使用Playwright），支持自动重连"""
        if not self._token_id:
            raise Exception("Token ID未获取，请先完成登录和会话初始化")

        try:
            # 创建带重连机制的WebSocket客户端（最多重连3次）
            self.ws_client = PlaywrightWSClient(max_retries=3)

            logger.info("🚀 启动Playwright WebSocket客户端（支持自动重连）...")
            success = await self.ws_client.start_monitoring(
                self._token_id,
                self.handle_websocket_message
            )

            if not success:
                logger.error("Playwright WebSocket连接失败，已达到最大重连次数")
                return False

            return True

        except Exception as e:
            logger.error(f"启动WebSocket监听失败: {e}")
            return False

    async def setup_auto_reply(self):
        """设置自动回复处理器"""
        if not self._auth_token:
            raise Exception("请先登录获取认证token")

        self.message_handler = IntegratedMessageHandler(
            dify_url=Config.DIFY_URL,
            dify_api_key=Config.DIFY_API_KEY,
            input_params=Config.INPUT_PARAMS,
            send_url=Config.SEND_MSG_URL,
            auth_token=self._auth_token,
            client=self  # 传入self用于调用set_read接口
        )
        logger.info("自动回复处理器初始化完成")

    async def setup_conversation_monitor(self, user_id: str):
        """设置对话监听服务"""
        if not self._auth_token:
            raise Exception("请先登录获取认证token")

        if not self.message_handler:
            raise Exception("请先初始化消息处理器")

        input_params = Config.INPUT_PARAMS.copy()
        input_params["is_return_visit"] = 1
        # 创建监听服务
        self.conversation_monitor = ConversationMonitor(
            db_path="conversations.db",
            dify_url=Config.DIFY_URL,
            dify_api_key=Config.DIFY_API_KEY,
            dify_input_params=input_params,
            cs_id=user_id,
            send_message_callback=self.message_handler.send_message_callback,
            check_interval=30,  # 每30秒检查一次
            stale_hours=3,     # 超过3小时未更新
            max_active_count=3  # 最多主动拜访3次
        )

        # 启动监听服务
        await self.conversation_monitor.start()
        logger.info("对话监听服务已启动")

    async def handle_websocket_message(self, raw_text: str) -> None:
        """处理WebSocket消息的回调函数"""
        banner = f"""
        ════════════════════════════════════════════════════════════════
          "收到WebSocket消息: {raw_text}"                              
        ════════════════════════════════════════════════════════════════
        """
        logger.debug(banner)

        if not self.message_handler:
            logger.error("自动回复处理器未初始化")
            return

        try:
            # 使用集成的消息处理器处理消息
            await self.message_handler.handle_websocket_message(raw_text)
        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {e}")

    async def start_auto_reply(self):
        """启动自动回复功能"""
        try:
            # 登录流程
            logger.info("开始登录...")
            await self.login()

            # 获取用户信息
            logger.info("获取用户信息...")
            await self.get_user_info()

            # 获取会话信息
            logger.info("获取会话信息...")
            await self.get_session_info()

            # 设置自动回复（必须在处理历史消息之前初始化）
            logger.info("初始化自动回复处理器...")
            await self.setup_auto_reply()

            # # 获取未读消息数量并处理历史未读消息
            # logger.info("获取未读消息数量...")
            # not_read_message_count = await self.get_not_read_message_count()
            # if not_read_message_count > 0:
            #     # 获取账号信息并处理历史未读消息
            #     logger.info(f"检测到 {not_read_message_count} 条未读消息，开始处理...")
            #     await self.get_account_info()
            #     logger.info("历史未读消息处理完成")

            # 启动对话监听服务
            logger.info("启动对话监听服务...")
            await self.setup_conversation_monitor(self._user_id)

            logger.info("🚀 自动回复机器人启动成功!")
            logger.info("正在监听WebSocket消息... (按Ctrl+C退出)")

            # 建立并维持 WebSocket 连接（使用Playwright）
            await self.start_websocket_monitoring()

        except Exception as e:
            logger.error(f"启动自动回复时出错: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        try:
            if self.conversation_monitor:
                await self.conversation_monitor.stop()
            if self.ws_client:
                await self.ws_client.close()
            if self.message_handler:
                await self.message_handler.close()
            await self.close()
            logger.info("资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")