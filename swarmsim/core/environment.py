"""
Environment Module - 上帝环境模块

维护全局时间线、环境变量和事件流，是所有 Agent 共享的"世界状态"。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4


class WeatherCondition(Enum):
    """天气状况"""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    INDOOR = "indoor"  # 室内场景


@dataclass
class EnvironmentEvent:
    """环境事件"""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: str = "general"
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "environment"
    severity: float = 0.5  # 0-1，影响程度
    metadata: dict = field(default_factory=dict)


class EnvironmentState:
    """
    环境状态管理

    维护世界的全局变量和条件。
    """

    def __init__(
        self,
        name: str = "Default World",
        weather: WeatherCondition = WeatherCondition.INDOOR,
        temperature: float = 25.0,
        time_of_day: str = "morning"  # morning, afternoon, evening, night
    ):
        self.name = name
        self.weather = weather
        self.temperature = temperature
        self.time_of_day = time_of_day
        self.global_mood = 0.5  # 0-1，群体情绪
        self.tension_level = 0.0  # 0-1，紧张程度

    def update_mood(self, delta: float) -> None:
        """更新群体情绪"""
        self.global_mood = max(0, min(1, self.global_mood + delta))

    def update_tension(self, delta: float) -> None:
        """更新紧张程度"""
        self.tension_level = max(0, min(1, self.tension_level + delta))

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "name": self.name,
            "weather": self.weather.value,
            "temperature": self.temperature,
            "time_of_day": self.time_of_day,
            "global_mood": self.global_mood,
            "tension_level": self.tension_level
        }


class Environment:
    """
    上帝环境模块

    管理仿真世界的全局状态、时间推进和事件广播。
    所有 Agent 通过 Environment 感知世界变化。
    """

    def __init__(
        self,
        name: str = "Simulation World",
        tick_interval: float = 1.0,
        max_events: int = 1000
    ):
        # 基础配置
        self.name = name
        self.tick_interval = tick_interval
        self.max_events = max_events

        # 状态
        self.state = EnvironmentState(name=name)
        self.current_time = datetime.now()
        self.current_turn = 0
        self.is_running = False

        # 事件系统
        self.events: list[EnvironmentEvent] = []
        self.event_listeners: list[callable] = []

        # Agent 注册
        self.agents: dict[str, Any] = {}

        # 广播板 - 公共信息区域
        self.broadcasts: list[dict] = []

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """注册 Agent 到环境"""
        self.agents[agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """注销 Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]

    def add_event(
        self,
        event_type: str,
        description: str,
        severity: float = 0.5,
        source: str = "environment",
        metadata: dict | None = None
    ) -> EnvironmentEvent:
        """添加环境事件"""
        event = EnvironmentEvent(
            type=event_type,
            description=description,
            timestamp=self.current_time,
            source=source,
            severity=severity,
            metadata=metadata or {}
        )

        self.events.append(event)

        # 限制事件数量
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        # 通知所有监听者
        self._notify_event_listeners(event)

        return event

    def broadcast(
        self,
        message: str,
        source: str = "system",
        importance: float = 0.5
    ) -> None:
        """向所有 Agent 广播消息"""
        broadcast = {
            "timestamp": self.current_time.isoformat(),
            "message": message,
            "source": source,
            "importance": importance
        }

        self.broadcasts.append(broadcast)

        # 通知所有 Agent
        for agent in self.agents.values():
            if hasattr(agent, "perceive"):
                agent.perceive({
                    "type": "broadcast",
                    "content": message,
                    "source": source
                })

    def _notify_event_listeners(self, event: EnvironmentEvent) -> None:
        """通知事件监听者"""
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception:
                pass

    def on_event(self, callback: callable) -> None:
        """注册事件监听器"""
        self.event_listeners.append(callback)

    def advance_time(self, minutes: int = 10) -> None:
        """推进时间"""
        self.current_time += timedelta(minutes=minutes)

        # 更新一天中的时段
        hour = self.current_time.hour
        if 6 <= hour < 12:
            self.state.time_of_day = "morning"
        elif 12 <= hour < 18:
            self.state.time_of_day = "afternoon"
        elif 18 <= hour < 22:
            self.state.time_of_day = "evening"
        else:
            self.state.time_of_day = "night"

    def advance_turn(self) -> None:
        """推进一个回合"""
        self.current_turn += 1
        self.advance_time()

    def get_recent_events(self, n: int = 5) -> list[EnvironmentEvent]:
        """获取最近的事件"""
        return self.events[-n:]

    def get_description(self) -> str:
        """获取环境描述"""
        time_desc = {
            "morning": "上午",
            "afternoon": "下午",
            "evening": "傍晚",
            "night": "夜晚"
        }

        weather_desc = {
            WeatherCondition.SUNNY: "晴朗",
            WeatherCondition.CLOUDY: "多云",
            WeatherCondition.RAINY: "下雨",
            WeatherCondition.STORMY: "暴风雨",
            WeatherCondition.INDOOR: "室内"
        }

        desc = f"""
=== {self.name} ===
时间: {time_desc.get(self.state.time_of_day, self.state.time_of_day)}
天气: {weather_desc.get(self.state.weather, self.state.weather.value)}
温度: {self.state.temperature}°C
群体情绪: {self._describe_mood()}
紧张程度: {self._describe_tension()}
当前回合: {self.current_turn}
"""
        return desc

    def _describe_mood(self) -> str:
        """描述群体情绪"""
        mood = self.state.global_mood
        if mood > 0.7:
            return "高涨 😊"
        elif mood > 0.4:
            return "平稳 😐"
        elif mood > 0.2:
            return "低落 😔"
        else:
            return "恶劣 😞"

    def _describe_tension(self) -> str:
        """描述紧张程度"""
        tension = self.state.tension_level
        if tension > 0.7:
            return "非常紧张 ⚠️"
        elif tension > 0.4:
            return "有些紧张"
        elif tension > 0.2:
            return "略有紧张"
        else:
            return "轻松"

    def get_agent_ids(self) -> list[str]:
        """获取所有注册的 Agent ID"""
        return list(self.agents.keys())

    def get_agent_count(self) -> int:
        """获取 Agent 数量"""
        return len(self.agents)

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "name": self.name,
            "state": self.state.to_dict(),
            "current_time": self.current_time.isoformat(),
            "current_turn": self.current_turn,
            "agent_count": self.get_agent_count(),
            "event_count": len(self.events),
            "recent_events": [
                {
                    "type": e.type,
                    "description": e.description,
                    "severity": e.severity
                }
                for e in self.get_recent_events(3)
            ]
        }

    def reset(self) -> None:
        """重置环境"""
        self.current_turn = 0
        self.current_time = datetime.now()
        self.events = []
        self.broadcasts = []
        self.state.global_mood = 0.5
        self.state.tension_level = 0.0

    async def run(self, duration: int | None = None) -> None:
        """
        运行环境主循环

        Args:
            duration: 运行回合数，None 表示无限运行
        """
        self.is_running = True
        target_turn = self.current_turn + duration if duration else None

        while self.is_running:
            if target_turn is not None and self.current_turn >= target_turn:
                break

            # 推进回合
            self.advance_turn()

            # 触发环境事件
            await self._process_turn()

            # 等待下一个 tick
            await asyncio.sleep(self.tick_interval)

    async def _process_turn(self) -> None:
        """处理一个回合"""
        # 可以在这里添加环境自动事件
        pass

    def stop(self) -> None:
        """停止环境运行"""
        self.is_running = False


class VarietyShowEnvironment(Environment):
    """
    综艺节目专用环境

    添加任务系统、预算限制等综艺节目特有的机制。
    """

    def __init__(
        self,
        name: str = "综艺修罗场",
        initial_budget: float = 1000.0,
        task_complexity: float = 0.5
    ):
        super().__init__(name=name)
        self.budget = initial_budget
        self.initial_budget = initial_budget
        self.task_complexity = task_complexity
        self.current_task = ""
        self.task_deadline: datetime | None = None

        # 综艺特有属性
        self.camera_on = False  # 是否在录制
        self.screen_time: dict[str, int] = {}  # 每个人的出镜时长

    def set_task(
        self,
        task: str,
        deadline_hours: int = 24
    ) -> None:
        """设置当前任务"""
        self.current_task = task
        self.task_deadline = self.current_time + timedelta(hours=deadline_hours)
        self.broadcast(f"新任务发布: {task}", source="director", importance=0.9)

    def consume_budget(self, amount: float, agent_id: str) -> bool:
        """消耗预算"""
        if self.budget >= amount:
            self.budget -= amount
            self.add_event(
                event_type="budget",
                description=f"{agent_id} 消耗了 {amount} 预算",
                severity=0.3
            )
            return True
        else:
            self.broadcast(
                f"预算不足！当前剩余: {self.budget}",
                source="system",
                importance=0.8
            )
            self.state.update_tension(0.2)
            return False

    def record_screen_time(self, agent_id: str, minutes: int) -> None:
        """记录出镜时长"""
        if agent_id not in self.screen_time:
            self.screen_time[agent_id] = 0
        self.screen_time[agent_id] += minutes

    def get_screen_time_ranking(self) -> list[tuple[str, int]]:
        """获取出镜时长排名"""
        return sorted(
            self.screen_time.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def get_description(self) -> str:
        """获取环境描述（综艺版）"""
        base_desc = super().get_description()

        budget_ratio = self.budget / self.initial_budget if self.initial_budget > 0 else 0
        budget_status = "充裕" if budget_ratio > 0.5 else "紧张" if budget_ratio > 0.2 else "告急"

        extra = f"""
=== 综艺节目状态 ===
当前任务: {self.current_task or "无"}
预算剩余: {self.budget:.1f} ({budget_status})
任务截止: {self.task_deadline.strftime('%H:%M') if self.task_deadline else '无'}
录制状态: {'🔴 录制中' if self.camera_on else '⏸️ 未录制'}
任务难度: {'困难' if self.task_complexity > 0.7 else '中等' if self.task_complexity > 0.4 else '简单'}
"""
        return base_desc + extra

    def trigger_drama_event(self) -> None:
        """触发戏剧性事件"""
        events = [
            ("director_cut", "导演突然喊卡，要求重拍！", 0.6),
            ("budget_warning", "财务组发出预算警告", 0.5),
            ("schedule_change", "行程突然变更", 0.5),
            ("conflict_escalation", "成员间发生争执", 0.7),
            ("weather_issue", "天气原因导致计划变更", 0.4),
        ]

        import random
        event_type, desc, severity = random.choice(events)

        self.add_event(event_type, desc, severity)
        self.broadcast(desc, source="production", importance=severity)
        self.state.update_tension(severity * 0.3)

    def reset(self) -> None:
        """重置综艺环境"""
        super().reset()
        self.budget = self.initial_budget
        self.current_task = ""
        self.task_deadline = None
        self.screen_time = {}
