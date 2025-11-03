#!/usr/bin/env python3
"""
RocketGo 自动回复机器人 - 主入口文件

这是一个智能客服自动回复机器人，具备以下功能：
- 自动登录RocketGo平台
- 监听WebSocket消息
- 调用Dify AI API生成智能回复
- 自动发送回复消息
- 使用SQLite持久化对话状态
- 定时重启机制（1-3小时随机）以保持连接活性

使用方法：
    python main.py

配置方法：
    1. 直接修改config.py中的配置项
    2. 或者通过环境变量设置（推荐）

示例环境变量：
    export ROCKETGO_USER="your_username"
    export ROCKETGO_PASS="your_password"
    export DIFY_API_KEY="your_dify_api_key"
"""

import asyncio
import logging
import sys
import random

from config import Config
from client import RocketGoClient
from logger_config import setup_logging, print_startup_banner, print_status_message

async def run_with_timeout(client: RocketGoClient):
    """运行客户端，并在指定时间后自动停止（1-3小时随机）"""
    logger = logging.getLogger(__name__)

    # 生成1-3小时之间的随机秒数 (1*3600 ~ 3*3600)
    timeout_seconds = random.randint(1 * 3600, 3 * 3600)
    timeout_hours = timeout_seconds / 3600

    logger.info(f"⏰ 本次运行时长设置为: {timeout_hours:.2f} 小时 ({timeout_seconds} 秒)")
    print_status_message(f"⏰ 本次运行时长: {timeout_hours:.2f} 小时", "info")

    try:
        # 创建运行任务
        run_task = asyncio.create_task(client.start_auto_reply())

        # 创建超时任务
        timeout_task = asyncio.create_task(asyncio.sleep(timeout_seconds))

        # 等待任一任务完成
        done, pending = await asyncio.wait(
            {run_task, timeout_task},
            return_when=asyncio.FIRST_COMPLETED
        )

        # 检查哪个任务完成了
        if timeout_task in done:
            # 超时了，需要重启
            logger.info("⏰ 运行时间到达，准备重启...")
            print_status_message("⏰ 运行时间到达，准备重启...", "warning")

            # 取消运行任务
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

            # 清理资源
            await client.cleanup()

            return "restart"  # 返回重启标志
        else:
            # 客户端正常退出或出错
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

            # 检查运行任务的结果
            if run_task.exception():
                raise run_task.exception()

            return "exit"  # 正常退出

    except asyncio.CancelledError:
        logger.info("运行被取消")
        return "exit"
    except Exception as e:
        logger.error(f"运行出错: {e}")
        raise

async def main():
    """主函数 - 带自动重启机制"""
    # 设置彩色日志
    setup_logging(Config.LOG_LEVEL, Config.LOG_FILE, use_colors=True)
    logger = logging.getLogger(__name__)

    # 打印启动横幅
    print_startup_banner()

    restart_count = 0  # 重启计数器

    while True:
        # 创建客户端
        client = RocketGoClient()

        try:
            if restart_count == 0:
                print_status_message("启动自动回复机器人...", "loading")
                logger.info("🚀 启动自动回复机器人...")
            else:
                print_status_message(f"重启自动回复机器人... (第 {restart_count} 次重启)", "loading")
                logger.info(f"🔄 重启自动回复机器人... (第 {restart_count} 次重启)")

            # 运行客户端（带超时）
            result = await run_with_timeout(client)

            if result == "restart":
                # 需要重启
                restart_count += 1
                logger.info(f"💫 准备进行第 {restart_count} 次重启，等待5秒...")
                print_status_message(f"等待5秒后重启... (已重启 {restart_count} 次)", "info")
                await asyncio.sleep(5)  # 等待5秒后重启
                continue
            else:
                # 正常退出
                logger.info("程序正常退出")
                print_status_message("程序正常退出", "info")
                return 0

        except KeyboardInterrupt:
            print_status_message("收到退出信号，正在停止程序...", "warning")
            logger.info("收到退出信号，正在停止程序...")
            await client.cleanup()
            return 0
        except Exception as e:
            print_status_message(f"程序运行出错: {e}", "error")
            logger.error(f"程序运行出错: {e}", exc_info=True)

            # 出错后也尝试重启（但增加重启计数）
            restart_count += 1
            logger.info(f"⚠️  出错后准备重启，等待10秒... (已重启 {restart_count} 次)")
            print_status_message(f"出错后等待10秒重启... (已重启 {restart_count} 次)", "warning")
            await asyncio.sleep(10)  # 出错后等待更长时间
            continue

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_status_message("程序已手动终止", "warning")
        sys.exit(0)
    except Exception as e:
        print_status_message(f"程序异常退出: {e}", "error")
        sys.exit(1)