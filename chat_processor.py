#!/usr/bin/env python3
"""
消息处理模块 - 处理WebSocket消息并调用Dify API
"""

import json
import logging
from typing import Dict, Any, Optional

from dify_client import DifyChatBot
from message_splitter import MessageSplitter

logger = logging.getLogger(__name__)

class MessageProcessor:
    """消息处理器 - 处理WebSocket接收的消息并调用Dify"""

    def __init__(self, dify_url: str, dify_api_key: str, input_params:dict, send_message_callback=None, client=None, db_path: str = "conversations.db"):
        self.chatbot = DifyChatBot(dify_url, dify_api_key, input_params, db_path)
        self.send_message_callback = send_message_callback
        self.client = client  # RocketGoClient实例，用于调用set_read接口
        self.message_splitter = MessageSplitter(delimiter="&&&")  # 初始化消息分段器

    def extract_message_info(self, raw_message: str) -> Optional[Dict[str, Any]]:
        """从WebSocket消息中提取用户信息和消息内容"""
        try:
            data = json.loads(raw_message)

            send_type = data.get('sendType')

            # 检查是否是异常响应（用户发送的消息）
            if send_type == 1:
                # sendType == 1 是正常响应，不需要处理
                logger.debug("收到正常响应消息，跳过处理")
                return None
            elif send_type == 2:  # 异常响应表示是用户消息
                send_info = data.get("sendInfo", {})
                sms = send_info.get("sms", {})
                # 检查是否是未发送的消息（isSend == 0）
                if send_info and send_info.get("isSend") == 0:
                    return {
                        "user_id": str(send_info.get("username", "")),  # 用户ID
                        "message_content": send_info.get("chatContent", ""),  # 消息内容
                        "cs_username": str(send_info.get("csUsername", "")),  # 客服账号
                        "cs_id": send_info.get("csId", ""),  # 客服ID
                        "cs_chat_user_id": send_info.get("csChatUserId", ""),  # 对话用户ID
                        "chat_type": 1,  # 聊天类型
                        "login": send_info.get("login", ""),  # 登录信息
                        "message_id": send_info.get("messageId", ""),  # 消息ID
                        "chat_id": str(send_info.get("id", "")),  # 用于标记已读的消息ID
                        "sms": sms  # 短信内容
                    }
                else:
                    logger.debug("收到已发送的消息，跳过处理")
                    return None
            elif send_type == 6:
                # sendType == 6 是对方已读事件，不需要处理
                logger.debug("收到对方已读事件，跳过处理")
                return None
            elif send_type == 7:
                # sendType == 7 是我们发送过去的消息，不需要处理
                logger.debug("收到我们发送过去的消息，跳过处理")
                return None
            elif send_type == 10:
                # sendType == 10 是系统消息，不需要处理
                logger.debug("收到系统消息，跳过处理")
                return None
            else:
                # sendType 未知，返回None
                logger.warning(f"未知的sendType: {send_type}, 消息内容: {data}")
                return None

        except json.JSONDecodeError:
            logger.error(f"无法解析JSON消息: {raw_message}")
            return None
        except Exception as e:
            logger.error(f"提取消息信息时出错: {e}")
            return None

    async def process_message(self, raw_message: str) -> Optional[str]:
        """处理单条消息"""
        # 提取消息信息
        message_info = self.extract_message_info(raw_message)
        if not message_info:
            return None

        user_id = message_info["user_id"]
        chat_id = message_info.get("chat_id", "")

        sms = message_info.get("sms", {})
        msg_type = sms.get("type", "")

        # if not sms or not isinstance(sms, dict):
        #     logger.error("短信内容为空或者不是字典类型")
        #     if msg_type != 9: return None
        #     sms["text"] = message_info["message_content"]
        # 1 表示图片消息 2 表示文件消息 3 表示视频消息 4 表示音频消息 7 表示名片消息 8 表示GIF消息 9 表示文本消息
        files = None
        if msg_type == 1:
            image_url = sms.get("imageUrl", "") or sms.get("fileUrl", "")
            logger.info(f"处理用户 {user_id} 的图片消息: {image_url}")
            message_content = sms.get("caption", " ")
            files = [
                      {
                          "type": "image",
                          "transfer_method": "remote_url",
                          "url": image_url
                      }
                  ]
        elif msg_type == 2:
            file_url = sms.get('fileUrl', '')
            logger.error(f"接收用户 {user_id} 的文件消息, 文件昵称: {sms.get('fileName', '无昵称')}，文件URL: {file_url}，文件大小: {sms.get('fileLength', '未知')}, 不处理该类型事件")
            return None

        elif msg_type == 3:
            video_url = sms["fileUrl"]
            logger.info(f"处理用户 {user_id} 的视频消息: {video_url}")
            message_content = sms.get("caption", " ")
            files = [
                      {
                          "type": "video",
                          "transfer_method": "remote_url",
                          "url": video_url
                      }
                  ]
        elif msg_type == 4:
            audio_url = sms["fileUrl"]
            logger.info(f"处理用户 {user_id} 的音频消息: {audio_url}")
            message_content = sms.get("caption", " ")
            files = [
                      {
                          "type": "audio",
                          "transfer_method": "remote_url",
                          "url": audio_url
                      }
                  ]
        elif msg_type == 7:
            logger.info(f"处理用户 {user_id} 的名片消息: 昵称: {sms.get('displayName', '无昵称')}，联系电话: {sms.get('getUsername', '无联系电话')} 不处理该类型事件")
            return None

        elif msg_type == 8:
            video_url = sms["fileUrl"]
            logger.info(f"处理用户 {user_id} 的GIF消息: {video_url}")
            message_content = sms.get("caption", " ")
            files = [
                      {
                          "type": "video",
                          "transfer_method": "remote_url",
                          "url": video_url
                      }
                  ]
        # elif msg_type == 9:
        #     message_content = sms["text"]
        #     logger.info(f"处理用户 {user_id} 的文本消息: {message_content}")
        else:
            message_content = sms.get("text", message_info["message_content"])
            logger.info(f"处理用户 {user_id} 的文本消息: {message_content}")
            # logger.error(f"未知的消息类型: {msg_type}")
            # return None
        try:
            # 立即调用set_read接口，标记消息已读
            if self.client and chat_id:
                try:
                    await self.client.set_read(chat_id)
                    logger.info(f"已标记消息 {chat_id} 为已读")
                except Exception as e:
                    logger.error(f"标记消息已读失败: {e}")
                    # 不影响后续处理，继续执行

            # 设置用户ID并获取Dify响应
            self.chatbot.set_user(message_info["cs_chat_user_id"], message_info["cs_username"], user_id)

            # 调用Dify API获取回复
            response = await self.chatbot.chat_completion(message_content, files, stream=False)

            # 更新时间戳
            self.chatbot.update_time()

            if response and response.get("answer"):
                reply_content = response["answer"]
                logger.info(f"Dify回复: {reply_content}")

                if reply_content == "END":
                    logger.info("收到END信号，结束对话")
                    return reply_content

                # 如果有发送回调，则发送回复消息
                if self.send_message_callback:
                    message_segments = self.message_splitter.split_message(reply_content)
                    
                    if message_segments:
                        # 分句发送
                        for i, segment in enumerate(message_segments, 1):
                            logger.info(f"正在发送第 {i}/{len(message_segments)} 段")
                            await self.send_message_callback(message_info, segment)
                        
                        logger.info(f"所有分句已发送")
                    else:
                        logger.warning("分句结果为空")

                return reply_content
            else:
                logger.warning("Dify未返回有效回复")
                return None

        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            return None


