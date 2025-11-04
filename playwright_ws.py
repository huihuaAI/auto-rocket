#!/usr/bin/env python3
"""
Playwright WebSocket客户端 - 绕过Cloudflare保护
通过浏览器环境建立WebSocket连接
"""

import asyncio
import logging
import sys
from typing import Callable, Optional
from pathlib import Path

from playwright.async_api import async_playwright
from config import Config

logger = logging.getLogger(__name__)


def get_chromium_executable_path():
    """获取 Chromium 可执行文件路径（兼容打包环境）"""
    # 检查是否在 PyInstaller 打包环境中
    if getattr(sys, 'frozen', False):
        # 打包环境
        if sys.platform == 'darwin':  # macOS
            base_path = Path(sys._MEIPASS)
            executable_path = base_path / 'playwright' / 'driver' / 'package' / '.local-browsers' / \
                            'chromium_headless_shell-1187' / 'chrome-mac' / 'headless_shell'
        elif sys.platform == 'win32':  # Windows
            base_path = Path(sys._MEIPASS)
            executable_path = base_path / 'playwright' / 'driver' / 'package' / '.local-browsers' / \
                            'chromium_headless_shell-1187' / 'chrome-win' / 'headless_shell.exe'
        else:  # Linux
            base_path = Path(sys._MEIPASS)
            executable_path = base_path / 'playwright' / 'driver' / 'package' / '.local-browsers' / \
                            'chromium_headless_shell-1187' / 'chrome-linux' / 'headless_shell'

        if executable_path.exists():
            logger.info(f"使用打包的浏览器: {executable_path}")
            return str(executable_path)
        else:
            logger.warning(f"打包的浏览器不存在: {executable_path}")
            return None
    else:
        # 开发环境，使用默认路径
        logger.info("使用系统安装的浏览器（开发模式）")
        return None  # None 表示使用 Playwright 默认路径

class PlaywrightWSClient:
    """使用Playwright建立WebSocket连接的客户端"""

    def __init__(self, message_handler: Optional[Callable] = None, max_retries: int = 3):
        self.message_handler = message_handler
        self.browser = None
        self.page = None
        self.is_connected = False
        self.max_retries = max_retries  # 最大重连次数
        self.current_retry = 0  # 当前重连次数
        self.token_id = None  # 保存token_id用于重连

    async def setup_browser(self):
        """设置浏览器环境"""
        try:
            self.playwright = await async_playwright().start()

            # 获取浏览器可执行文件路径
            executable_path = get_chromium_executable_path()

            # 启动浏览器（使用headless模式）
            launch_options = {
                'headless': True,
                'args': ['--disable-web-security', '--disable-features=VizDisplayCompositor']
            }

            # 如果有指定的浏览器路径，使用它
            if executable_path:
                launch_options['executable_path'] = executable_path

            self.browser = await self.playwright.chromium.launch(**launch_options)

            # 创建新页面
            self.page = await self.browser.new_page()

            # 监听浏览器控制台输出（用于调试）
            self.page.on("console", lambda msg: logger.debug(f"[浏览器] {msg.text}"))

            # 设置用户代理
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            logger.info("浏览器环境设置完成")
            return True

        except Exception as e:
            logger.error(f"设置浏览器环境失败: {e}")
            return False

    async def setup_message_handler(self):
        """设置消息处理回调"""
        if not self.page:
            raise Exception("浏览器页面未初始化")

        # 暴露Python函数给浏览器调用
        async def handle_message(source, message):
            """处理从浏览器传来的WebSocket消息"""
            try:
                if self.message_handler:
                    await self.message_handler(message)
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {e}")

        # 将消息处理函数暴露给浏览器
        await self.page.expose_binding("sendToPython", handle_message)
        logger.info("消息处理回调已设置")

    async def connect_websocket(self, token_id: str):
        """建立WebSocket连接"""
        if not self.page:
            raise Exception("浏览器页面未初始化")

        try:
            # 首先访问网站建立Cloudflare信任会话
            logger.info("正在访问网站建立Cloudflare信任会话...")
            await self.page.goto("https://pn3cs.rocketgo.vip", wait_until="domcontentloaded")

            # 构建WebSocket URL
            ws_url = f"{Config.WS_URL}/{token_id}"
            logger.info(f"准备建立WebSocket连接: {ws_url}")

            # 在浏览器中执行WebSocket连接代码
            await self.page.evaluate(f"""
                const ws = new WebSocket("{ws_url}");

                // 心跳相关变量
                window.heartbeatInterval = null;
                window.heartbeatTimeout = null;
                window.lastHeartbeatTime = Date.now();
                window.missedHeartbeats = 0;
                window.connectionLost = false;  // 新增：标记连接是否真的丢失
                const MAX_MISSED_HEARTBEATS = 2;  // 减少到2次，更快检测到问题
                const HEARTBEAT_INTERVAL = 5000;   // 5秒发送一次心跳
                const HEARTBEAT_TIMEOUT = 8000;    // 8秒未收到响应视为超时

                // 清理心跳定时器
                function clearHeartbeat() {{
                    if (window.heartbeatInterval) {{
                        clearInterval(window.heartbeatInterval);
                        window.heartbeatInterval = null;
                    }}
                    if (window.heartbeatTimeout) {{
                        clearTimeout(window.heartbeatTimeout);
                        window.heartbeatTimeout = null;
                    }}
                }}

                // 标记连接丢失
                function markConnectionLost() {{
                    console.error("❌ 连接丢失，标记需要重连");
                    window.wsConnected = false;
                    window.connectionLost = true;
                    clearHeartbeat();

                    // 尝试关闭WebSocket（即使可能已经断开）
                    try {{
                        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {{
                            ws.close();
                        }}
                    }} catch (e) {{
                        console.error("关闭WebSocket时出错:", e);
                    }}
                }}

                // 发送心跳包
                function sendHeartbeat() {{
                    try {{
                        if (ws.readyState === WebSocket.OPEN) {{
                            ws.send("ping");
                            window.lastHeartbeatTime = Date.now();
                            console.log("💓 发送心跳包");

                            // 设置心跳超时检测
                            if (window.heartbeatTimeout) {{
                                clearTimeout(window.heartbeatTimeout);
                            }}
                            window.heartbeatTimeout = setTimeout(() => {{
                                window.missedHeartbeats++;
                                console.warn(`⚠️ 心跳响应超时 (已失败 ${{window.missedHeartbeats}}/${{MAX_MISSED_HEARTBEATS}}次)`);

                                if (window.missedHeartbeats >= MAX_MISSED_HEARTBEATS) {{
                                    console.error("❌ 心跳连续失败次数过多，判定连接已断开");
                                    markConnectionLost();
                                }}
                            }}, HEARTBEAT_TIMEOUT);
                        }} else if (ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {{
                            console.error("❌ WebSocket已关闭或正在关闭");
                            markConnectionLost();
                        }} else {{
                            console.warn("⚠️ WebSocket未处于OPEN状态，跳过本次心跳");
                            window.missedHeartbeats++;
                            if (window.missedHeartbeats >= MAX_MISSED_HEARTBEATS) {{
                                console.error("❌ WebSocket状态异常次数过多，判定连接已断开");
                                markConnectionLost();
                            }}
                        }}
                    }} catch (err) {{
                        console.error("❌ 发送心跳包失败:", err);
                        window.missedHeartbeats++;
                        if (window.missedHeartbeats >= MAX_MISSED_HEARTBEATS) {{
                            console.error("❌ 心跳发送失败次数过多，判定连接已断开");
                            markConnectionLost();
                        }}
                    }}
                }}

                ws.onopen = () => {{
                    console.log("✅ WebSocket已连接");
                    window.wsConnected = true;
                    window.connectionLost = false;
                    window.missedHeartbeats = 0;

                    // 启动心跳机制
                    clearHeartbeat();  // 清理可能存在的旧定时器
                    window.heartbeatInterval = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
                    console.log("💓 心跳机制已启动");
                }};

                ws.onmessage = (e) => {{
                    console.log("📨 收到WebSocket消息:", e.data);

                    // 收到任何消息都视为连接正常，重置心跳计数
                    window.missedHeartbeats = 0;
                    window.lastHeartbeatTime = Date.now();

                    // 清除心跳超时定时器
                    if (window.heartbeatTimeout) {{
                        clearTimeout(window.heartbeatTimeout);
                        window.heartbeatTimeout = null;
                    }}

                    window.sendToPython(e.data);
                }};

                ws.onerror = (err) => {{
                    console.error("❌ WebSocket错误:", err);
                    markConnectionLost();
                }};

                ws.onclose = (event) => {{
                    console.log(`🔌 WebSocket已关闭 (code: ${{event.code}}, reason: ${{event.reason}})`);
                    markConnectionLost();
                }};

                // 将WebSocket实例保存到window对象
                window.ws = ws;
            """)

            # 等待连接建立
            for i in range(10):  # 最多等待10秒
                try:
                    is_connected = await self.page.evaluate("window.wsConnected === true")
                    if is_connected:
                        self.is_connected = True
                        logger.info("WebSocket连接已建立")
                        return True
                except:
                    pass
                await asyncio.sleep(1)

            logger.error("WebSocket连接建立超时")
            return False

        except Exception as e:
            logger.error(f"建立WebSocket连接失败: {e}")
            return False

    async def check_websocket_health(self) -> bool:
        """主动检测 WebSocket 是否健康（通过发送 ping 并等待响应）"""
        try:
            # 记录 ping 发送时间
            await self.page.evaluate("""
                window.lastPingTime = Date.now();
                window.pingReceived = false;
            """)

            # 发送 ping
            await self.page.evaluate("""
                if (window.ws && window.ws.readyState === WebSocket.OPEN) {
                    window.ws.send("ping");
                    console.log("🔍 主动发送健康检查 ping");
                }
            """)

            # 等待最多 3 秒检查是否收到响应
            for _ in range(6):  # 6 * 0.5 = 3 秒
                await asyncio.sleep(0.5)

                # 检查是否收到了消息（任何消息都会重置 pingReceived）
                try:
                    ping_received = await self.page.evaluate("""
                        // 检查是否在发送 ping 后收到了消息
                        if (window.lastHeartbeatTime > window.lastPingTime) {
                            true;
                        } else {
                            false;
                        }
                    """)

                    if ping_received:
                        logger.debug("✅ WebSocket 健康检查通过")
                        return True
                except Exception as e:
                    logger.error(f"健康检查时出错: {e}")
                    return False

            # 3秒内没有收到任何响应
            logger.warning("⚠️ WebSocket 健康检查失败：3秒内未收到响应")
            return False

        except Exception as e:
            logger.error(f"WebSocket 健康检查异常: {e}")
            return False

    async def wait_for_messages(self):
        """保持连接并等待消息，返回是否需要重连"""
        if not self.is_connected:
            raise Exception("WebSocket连接未建立")

        logger.info("开始监听WebSocket消息...")
        last_health_check = asyncio.get_event_loop().time()
        health_check_interval = 15  # 每15秒做一次健康检查

        try:
            while True:
                current_time = asyncio.get_event_loop().time()

                # 检查连接状态
                try:
                    is_connected = await self.page.evaluate("window.wsConnected === true")
                    if not is_connected:
                        logger.warning("WebSocket 标志位显示连接已断开，需要重连")
                        return True  # 返回True表示需要重连
                except:
                    logger.error("无法检查连接状态，可能页面已关闭")
                    return True  # 返回True表示需要重连

                # 检查页面是否还活着（使用超时机制）
                try:
                    # 设置 3 秒超时，如果页面卡住了会抛出超时异常
                    await asyncio.wait_for(
                        self.page.evaluate("console.log('页面存活检查')"),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.error("页面响应超时（可能卡死），需要重连")
                    return True
                except Exception as e:
                    logger.error(f"页面可能已断开: {e}")
                    return True  # 返回True表示需要重连

                # 定期做主动健康检查（发送 ping 并验证能收到响应）
                if current_time - last_health_check >= health_check_interval:
                    logger.info("🔍 执行 WebSocket 主动健康检查...")
                    is_healthy = await self.check_websocket_health()

                    if not is_healthy:
                        logger.error("❌ WebSocket 健康检查失败，连接可能已僵死，需要重连")
                        return True  # 需要重连

                    last_health_check = current_time

                await asyncio.sleep(5)  # 每5秒检查一次基本状态

        except KeyboardInterrupt:
            logger.info("收到用户退出信号")
            return False  # 用户主动退出，不需要重连
        except Exception as e:
            logger.error(f"监听消息时出错: {e}")
            return True  # 异常情况，需要重连
        finally:
            self.is_connected = False

    async def close(self):
        """完全关闭连接和浏览器（用于最终清理）"""
        try:
            self.is_connected = False
            self.current_retry = self.max_retries + 1  # 停止重连机制

            if self.page:
                # 关闭WebSocket连接
                try:
                    await self.page.evaluate("""
                        if (window.ws) {
                            window.ws.close();
                            console.log("WebSocket连接已关闭");
                        }
                    """)
                except:
                    pass

                await self.page.close()
                self.page = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if hasattr(self, 'playwright'):
                await self.playwright.stop()

            logger.info("Playwright WebSocket客户端已完全关闭")

        except Exception as e:
            logger.error(f"关闭Playwright客户端时出错: {e}")

    async def start_monitoring(self, token_id: str, message_handler: Callable):
        """启动完整的监听流程，支持重连机制"""
        self.message_handler = message_handler
        self.token_id = token_id  # 保存token_id用于重连

        attempt = 0  # 尝试次数（从0开始，0表示首次连接）

        while attempt <= self.max_retries:
            try:
                if attempt == 0:
                    logger.info("开始首次连接...")
                else:
                    logger.info(f"开始第 {attempt} 次重连...")

                # 设置浏览器环境
                if not await self.setup_browser():
                    logger.error("设置浏览器环境失败")
                    attempt += 1
                    if attempt <= self.max_retries:
                        logger.info(f"等待 5 秒后重试...")
                        await asyncio.sleep(5)
                        continue
                    else:
                        break

                # 设置消息处理回调
                await self.setup_message_handler()

                # 建立WebSocket连接
                if not await self.connect_websocket(token_id):
                    logger.warning("建立WebSocket连接失败")
                    attempt += 1
                    if attempt <= self.max_retries:
                        logger.info(f"等待 5 秒后重试...")
                        await asyncio.sleep(5)
                        continue
                    else:
                        break

                # 连接成功，重置尝试计数器
                logger.info("✅ WebSocket连接成功建立！")
                attempt = 0

                # 开始监听消息
                need_reconnect = await self.wait_for_messages()

                if not need_reconnect:
                    # 用户主动退出或正常结束
                    logger.info("监听正常结束，无需重连")
                    return True
                else:
                    # 需要重连
                    attempt += 1
                    if attempt <= self.max_retries:
                        logger.warning(f"连接断开，准备进行第 {attempt} 次重连...")
                        logger.info("等待 5 秒后重连...")
                        await asyncio.sleep(5)
                        continue
                    else:
                        logger.error(f"已达到最大重连次数 {self.max_retries}，停止重连")
                        break

            except KeyboardInterrupt:
                logger.info("收到用户中断信号，停止重连")
                return False
            except Exception as e:
                logger.error(f"Playwright WebSocket监听出错: {e}")
                attempt += 1

                if attempt <= self.max_retries:
                    logger.info(f"等待 5 秒后进行第 {attempt} 次重连...")
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.error(f"已达到最大重连次数 {self.max_retries}，停止重连")
                    break
            finally:
                # 清理当前连接资源（但保留重连能力）
                try:
                    if self.page:
                        await self.page.close()
                        self.page = None
                    if self.browser:
                        await self.browser.close()
                        self.browser = None
                    if hasattr(self, 'playwright'):
                        await self.playwright.stop()
                except Exception as e:
                    logger.error(f"清理资源时出错: {e}")

        # 所有重连尝试都失败了
        logger.error(f"WebSocket连接最终失败（已尝试 {attempt} 次）")
        return False
