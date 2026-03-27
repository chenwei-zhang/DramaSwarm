"""
反爬虫工具 - 处理请求限流、User-Agent轮换等
"""

from __future__ import annotations

import random
import time
import asyncio
from dataclasses import dataclass, field


# 常见的浏览器User-Agent
USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",

    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",

    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",

    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

# 常见的请求头模板
HEADERS_TEMPLATES = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    },
]


@dataclass
class ProxyConfig:
    """代理配置"""
    enabled: bool = False
    proxy_list: list[str] = field(default_factory=list)
    rotate_every: int = 10  # 每N个请求轮换一次


class RateLimiter:
    """请求限流器"""

    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        requests_per_minute: int = 20
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_per_minute = requests_per_minute
        self.request_times = []

    async def acquire(self):
        """获取请求许可（等待如果需要）"""
        now = time.time()

        # 清理1分钟前的记录
        self.request_times = [t for t in self.request_times if now - t < 60]

        # 如果达到限制，等待
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # 随机延迟
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

        self.request_times.append(now)


class UserAgentRotator:
    """User-Agent轮换器"""

    def __init__(self, user_agents: list[str] | None = None):
        self.user_agents = user_agents or USER_AGENTS
        self.current_index = 0

    def get_random(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.user_agents)

    def get_next(self) -> str:
        """获取下一个User-Agent（轮换）"""
        ua = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return ua

    def get_headers(self) -> dict:
        """获取完整的请求头"""
        base_headers = random.choice(HEADERS_TEMPLATES).copy()
        base_headers["User-Agent"] = self.get_random()
        return base_headers


class SessionManager:
    """会话管理器 - 处理cookies、session等"""

    def __init__(self):
        self.cookies = {}
        self.session_count = 0

    def rotate_session(self):
        """轮换会话"""
        self.session_count += 1
        self.cookies = {}

    def get_cookies(self) -> dict:
        """获取当前cookies"""
        return self.cookies.copy()


def get_random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> float:
    """获取随机延迟时间"""
    return random.uniform(min_sec, max_sec)


async def smart_delay(
    base_delay: float = 1.0,
    jitter: float = 0.5,
    attempt: int = 1
):
    """
    智能延迟 - 随尝试次数增加延迟

    Args:
        base_delay: 基础延迟
        jitter: 抖动范围
        attempt: 当前尝试次数
    """
    # 指数退避 + 随机抖动
    delay = base_delay * (1.5 ** (attempt - 1))
    delay = delay + random.uniform(-jitter, jitter)
    delay = max(0.5, min(delay, 30))  # 限制在0.5-30秒之间

    await asyncio.sleep(delay)
