import asyncio
import websockets
import logging

from config import config

logger = logging.getLogger(__name__)



class WSClient:

    RECONNECT_DELAY = 5

    def __init__(self, token: str, message_handler=None):
        """初始化 WebSocket 客户端

        Args:
            token: 认证令牌
            message_handler: 消息处理回调函数 async def handler(message: str)
        """
        self.token = token
        self.message_handler = message_handler


    async def heartbeat(self, ws):
        """每 5 秒发送业务 ping"""
        while True:
            try:
                await ws.send("ping")
                logging.info("➡️ Ping sent (string)")
            except Exception as e:
                logging.error(f"Heartbeat send error: {e}")
                break
            await asyncio.sleep(5)


    async def listen(self, ws):
        """监听并处理来自服务器的消息"""
        try:
            async for raw in ws:
                logging.info(f"📨 Received: {raw}")

                # 如果设置了消息处理器，调用它
                if self.message_handler:
                    try:
                        await self.message_handler(raw)
                    except Exception as e:
                        logging.error(f"Message handler error: {e}", exc_info=True)
        except Exception as e:
            logging.error(f"Listen error: {e}")


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
                logging.error(f"⚠️ Connection lost: {e}")
                logging.info(f"⏳ Reconnect in {self.RECONNECT_DELAY}s...")
                await asyncio.sleep(self.RECONNECT_DELAY)


if __name__ == "__main__":
    asyncio.run(WSClient("d0ab9d1e-1be6-4883-8340-49a80a11c05c").connect())
