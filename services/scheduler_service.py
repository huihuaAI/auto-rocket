#!/usr/bin/env python3
"""
定时重启服务 - 定期重启RocketGo服务以刷新token
"""

import asyncio
import logging
import random
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时重启服务

    功能：
    - 定期重启WebSocket连接
    - 防止token过期（默认3小时）
    - 可配置重启间隔
    """

    def __init__(self,
                 restart_callback: Callable,
                 min_interval_hours: float = 1.0,
                 max_interval_hours: float = 3.0):
        """初始化定时服务

        Args:
            restart_callback: 重启回调函数（async）
            min_interval_hours: 最小重启间隔（小时）
            max_interval_hours: 最大重启间隔（小时）
        """
        self.restart_callback = restart_callback
        self.min_interval_hours = min_interval_hours
        self.max_interval_hours = max_interval_hours

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._next_restart_time: Optional[datetime] = None

    def start(self):
        """启动定时服务"""
        if self._running:
            logger.warning("定时服务已在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"定时重启服务已启动 - 重启间隔: {self.min_interval_hours}-{self.max_interval_hours}小时")

    async def stop(self):
        """停止定时服务"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._next_restart_time = None
        logger.info("定时重启服务已停止")

    def _get_random_interval(self) -> float:
        """获取随机重启间隔（秒）"""
        hours = random.uniform(self.min_interval_hours, self.max_interval_hours)
        return hours * 3600

    async def _scheduler_loop(self):
        """定时器循环"""
        while self._running:
            try:
                # 计算下次重启时间
                interval_seconds = self._get_random_interval()
                self._next_restart_time = datetime.now()
                import datetime as dt
                self._next_restart_time = datetime.now() + dt.timedelta(seconds=interval_seconds)

                logger.info(f"下次重启时间: {self._next_restart_time.strftime('%Y-%m-%d %H:%M:%S')}")

                # 等待到重启时间
                await asyncio.sleep(interval_seconds)

                if not self._running:
                    break

                # 执行重启
                logger.info("执行定时重启...")
                try:
                    await self.restart_callback()
                    logger.info("定时重启成功")
                except Exception as e:
                    logger.error(f"定时重启失败: {e}", exc_info=True)

            except asyncio.CancelledError:
                logger.info("定时服务被取消")
                break
            except Exception as e:
                logger.error(f"定时服务出错: {e}", exc_info=True)
                # 出错后等待一段时间再重试
                await asyncio.sleep(60)

    def is_running(self) -> bool:
        """判断定时服务是否正在运行"""
        return self._running

    def get_next_restart_time(self) -> Optional[str]:
        """获取下次重启时间的字符串表示"""
        if self._next_restart_time:
            return self._next_restart_time.strftime('%Y-%m-%d %H:%M:%S')
        return None

    def set_interval(self, min_hours: float, max_hours: float):
        """动态设置重启间隔

        Args:
            min_hours: 最小重启间隔（小时）
            max_hours: 最大重启间隔（小时）
        """
        self.min_interval_hours = min_hours
        self.max_interval_hours = max_hours
        logger.info(f"重启间隔已更新: {min_hours}-{max_hours}小时")
