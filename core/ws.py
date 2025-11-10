import asyncio
import websockets
import logging

from config import config

logger = logging.getLogger(__name__)



class WSClient:

    RECONNECT_DELAY = 5

    def __init__(self, token: str, message_handler=None, on_auth_error=None):
        """初始化 WebSocket 客户端

        Args:
            token: 认证令牌
            message_handler: 消息处理回调函数 async def handler(message: str)
            on_auth_error: 认证错误回调函数 async def handler() -> str | None (返回新token或None)
        """
        self.token = token
        self.message_handler = message_handler
        self.on_auth_error = on_auth_error


    async def heartbeat(self, ws):
        """每 5 秒发送业务 ping"""
        while True:
            try:
                await ws.send("ping")
                logging.info("➡️ Ping sent (string)")
            except Exception as e:
                logging.error(f"Heartbeat send error: {e}")
                raise  # 重新抛出异常，触发重连
            await asyncio.sleep(5)


    async def listen(self, ws):
        """监听并处理来自服务器的消息"""
        try:
            async for raw in ws:
                # 添加消息分隔线
                logging.info("━" * 80)
                
                # 尝试解析并简化JSON消息显示
                try:
                    import json
                    data = json.loads(raw)
                    
                    # 根据消息类型显示不同的关键信息
                    send_type = data.get('sendType')
                    
                    if send_type == 1:
                        # 心跳响应等简单消息
                        logging.info(f"📨 收到消息 [类型: {send_type}]")
                    elif send_type == 2 and 'sendInfo' in data:
                        # 聊天消息
                        send_info = data['sendInfo']
                        chat_content = send_info.get('chatContent', '')
                        notify = send_info.get('notify', '未知')
                        chat_type = send_info.get('chatType', 0)
                        
                        logging.info(f"📨 收到聊天消息 [类型: {send_type}]")
                        logging.info(f"  发送者: {notify}")
                        logging.info(f"  内容: {chat_content}")
                        logging.info(f"  会话类型: {chat_type}")
                    else:
                        # 其他类型消息，显示原始内容（截断过长内容）
                        display_raw = raw if len(raw) <= 200 else raw[:200] + "..."
                        logging.info(f"📨 收到消息: {display_raw}")
                        
                except json.JSONDecodeError:
                    # 非JSON消息，直接显示
                    logging.info(f"📨 收到消息: {raw}")
                except Exception as e:
                    # 解析出错，显示原始消息
                    logging.warning(f"消息解析失败: {e}，显示原始内容")
                    logging.info(f"📨 收到消息: {raw}")

                # 如果设置了消息处理器，调用它
                if self.message_handler:
                    try:
                        await self.message_handler(raw)
                    except Exception as e:
                        logging.error(f"Message handler error: {e}", exc_info=True)
                        
        except Exception as e:
            logging.error(f"Listen error: {e}")
            raise  # 重新抛出异常，触发重连  # 重新抛出异常，触发重连


    async def connect(self):
        """自动重连逻辑"""
        while True:
            try:
                logging.info("🔌 Connecting...")
                async with websockets.connect(
                    config.rocketgo.ws_url + f"/{self.token}",
                    ping_interval=None,  # 关闭协议层心跳
                ) as ws:
                    logging.info("✅ WebSocket Connected!")

                    await asyncio.gather(
                        self.listen(ws),
                        self.heartbeat(ws)
                    )

            except Exception as e:
                error_msg = str(e)
                
                # 检测 403 认证错误
                if "403" in error_msg and self.on_auth_error:
                    logging.warning("🔐 认证失败(403)，尝试重新登录...")
                    try:
                        new_token = await self.on_auth_error()
                        if new_token:
                            self.token = new_token
                            logging.info("✅ 重新登录成功，使用新token重连")
                            continue  # 立即重连，不等待
                        else:
                            logging.error("❌ 重新登录失败，停止重连")
                            break  # 退出重连循环
                    except Exception as auth_error:
                        logging.error(f"❌ 重新登录异常: {auth_error}")
                        break
                
                logging.error(f"⚠️ Connection lost: {e}")
                logging.info(f"⏳ Reconnect in {self.RECONNECT_DELAY}s...")
                await asyncio.sleep(self.RECONNECT_DELAY)


if __name__ == "__main__":
    asyncio.run(WSClient("d0ab9d1e-1be6-4883-8340-49a80a11c05c").connect())
