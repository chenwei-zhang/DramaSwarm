# -*- coding: utf-8 -*-
"""
Environment 基类 - 全局时间线、环境变量和事件流

所有 Agent 共享的"世界状态"，集成多层反应系统。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from .reaction_bus import ReactionBus


class WeatherCondition(Enum):
    """天气状况"""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    INDOOR = "indoor"


@dataclass
class EnvironmentEvent:
    """环境事件"""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: str = "general"
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "environment"
    severity: float = 0.5
    metadata: dict = field(default_factory=dict)


class EnvironmentState:
    """环境状态管理"""

    def __init__(
        self,
        name: str = "Default World",
        weather: WeatherCondition = WeatherCondition.INDOOR,
        temperature: float = 25.0,
        time_of_day: str = "morning",
    ):
        self.name = name
        self.weather = weather
        self.temperature = temperature
        self.time_of_day = time_of_day
        self.global_mood = 0.5
        self.tension_level = 0.0

    def update_mood(self, delta: float) -> None:
        self.global_mood = max(0, min(1, self.global_mood + delta))

    def update_tension(self, delta: float) -> None:
        self.tension_level = max(0, min(1, self.tension_level + delta))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "weather": self.weather.value,
            "temperature": self.temperature,
            "time_of_day": self.time_of_day,
            "global_mood": self.global_mood,
            "tension_level": self.tension_level,
        }


class Environment:
    """
    上帝环境模块

    管理仿真世界的全局状态、时间推进、事件广播和多層反應系統。
    """

    def __init__(
        self,
        name: str = "Simulation World",
        tick_interval: float = 1.0,
        max_events: int = 1000,
    ):
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

        # 广播板
        self.broadcasts: list[dict] = []

        # 多层反应系统
        self.reaction_bus = ReactionBus()

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """注册 Agent 到环境（含反应系统）"""
        self.agents[agent_id] = agent

        # 注册到反应系统
        agent_name = getattr(getattr(agent, "config", None), "name", None)
        if agent_name is None:
            agent_name = getattr(agent, "name", str(agent))
        self.reaction_bus.register_agent(agent_id, agent_name)

    def unregister_agent(self, agent_id: str) -> None:
        if agent_id in self.agents:
            del self.agents[agent_id]

    def add_event(
        self,
        event_type: str,
        description: str,
        severity: float = 0.5,
        source: str = "environment",
        metadata: dict | None = None,
    ) -> EnvironmentEvent:
        """添加环境事件，同时触发反应系统"""
        event = EnvironmentEvent(
            type=event_type,
            description=description,
            timestamp=self.current_time,
            source=source,
            severity=severity,
            metadata=metadata or {},
        )

        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        self._notify_event_listeners(event)

        # 触发多层反应
        context = {
            "event_id": event.id,
            "agents": self.agents,
            "turn": self.current_turn,
        }
        reactions = self.reaction_bus.dispatch(
            event_description=description,
            severity=severity,
            source=source,
            context=context,
        )

        # 反应事件也记录到环境事件流
        for reaction in reactions:
            self.events.append(EnvironmentEvent(
                type=f"reaction_{reaction.reaction_layer}",
                description=reaction.description,
                severity=reaction.severity,
                source=reaction.reaction_layer,
                metadata={"target_agents": reaction.target_agent_ids},
            ))

        # 反应影响情绪和紧张度
        if reactions:
            avg_severity = sum(r.severity for r in reactions) / len(reactions)
            self.state.update_mood(-avg_severity * 0.1)
            self.state.update_tension(avg_severity * 0.1)

        return event

    def broadcast(
        self,
        message: str,
        source: str = "system",
        importance: float = 0.5,
    ) -> None:
        """向所有 Agent 广播消息"""
        broadcast = {
            "timestamp": self.current_time.isoformat(),
            "message": message,
            "source": source,
            "importance": importance,
        }
        self.broadcasts.append(broadcast)

        for agent in self.agents.values():
            if hasattr(agent, "perceive"):
                agent.perceive({
                    "type": "broadcast",
                    "content": message,
                    "source": source,
                })

    def _notify_event_listeners(self, event: EnvironmentEvent) -> None:
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception:
                pass

    def on_event(self, callback: callable) -> None:
        self.event_listeners.append(callback)

    def advance_time(self, minutes: int = 10) -> None:
        self.current_time += timedelta(minutes=minutes)
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
        """推进一个回合（含反应衰减和快照）"""
        self.current_turn += 1
        self.advance_time()

        # 反应层数据衰减
        self.reaction_bus.decay()

        # 拍摄快照
        self.reaction_bus.take_snapshot(self.current_turn)

    def get_recent_events(self, n: int = 5) -> list[EnvironmentEvent]:
        return self.events[-n:]

    def get_description(self) -> str:
        """获取环境描述（含反应层摘要）"""
        time_desc = {
            "morning": "上午", "afternoon": "下午",
            "evening": "傍晚", "night": "夜晚",
        }
        weather_desc = {
            WeatherCondition.SUNNY: "晴朗",
            WeatherCondition.CLOUDY: "多云",
            WeatherCondition.RAINY: "下雨",
            WeatherCondition.STORMY: "暴风雨",
            WeatherCondition.INDOOR: "室内",
        }

        base = f"""
=== {self.name} ===
时间: {time_desc.get(self.state.time_of_day, self.state.time_of_day)}
天气: {weather_desc.get(self.state.weather, self.state.weather.value)}
温度: {self.state.temperature}°C
群体情绪: {self._describe_mood()}
紧张程度: {self._describe_tension()}
当前回合: {self.current_turn}
"""
        # 附加反应层描述
        reaction_desc = self.reaction_bus.get_description()
        if reaction_desc.strip():
            base += "\n" + reaction_desc

        return base

    def get_agent_reaction_context(self, agent_id: str) -> str:
        """获取某 agent 的个性化反应感知"""
        return self.reaction_bus.get_perception_for_agent(agent_id)

    def _describe_mood(self) -> str:
        mood = self.state.global_mood
        if mood > 0.7:
            return "高涨"
        elif mood > 0.4:
            return "平稳"
        elif mood > 0.2:
            return "低落"
        else:
            return "恶劣"

    def _describe_tension(self) -> str:
        tension = self.state.tension_level
        if tension > 0.7:
            return "非常紧张"
        elif tension > 0.4:
            return "有些紧张"
        elif tension > 0.2:
            return "略有紧张"
        else:
            return "轻松"

    def get_agent_ids(self) -> list[str]:
        return list(self.agents.keys())

    def get_agent_count(self) -> int:
        return len(self.agents)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.to_dict(),
            "current_time": self.current_time.isoformat(),
            "current_turn": self.current_turn,
            "agent_count": self.get_agent_count(),
            "event_count": len(self.events),
            "reactions": self.reaction_bus.get_state(),
            "recent_events": [
                {"type": e.type, "description": e.description, "severity": e.severity}
                for e in self.get_recent_events(3)
            ],
        }

    def reset(self) -> None:
        self.current_turn = 0
        self.current_time = datetime.now()
        self.events = []
        self.broadcasts = []
        self.state.global_mood = 0.5
        self.state.tension_level = 0.0
        self.reaction_bus.reset()

    async def run(self, duration: int | None = None) -> None:
        self.is_running = True
        target_turn = self.current_turn + duration if duration else None

        while self.is_running:
            if target_turn is not None and self.current_turn >= target_turn:
                break
            self.advance_turn()
            await self._process_turn()
            await asyncio.sleep(self.tick_interval)

    async def _process_turn(self) -> None:
        pass

    def stop(self) -> None:
        self.is_running = False
