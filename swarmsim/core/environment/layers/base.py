# -*- coding: utf-8 -*-
"""
反应层抽象基类
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ReactionEvent, EnvironmentReactionSnapshot


class ReactionLayer(ABC):
    """所有反应层的抽象基类"""

    layer_name: str = "base"

    @abstractmethod
    def react(self, event_description: str, severity: float,
              source: str, context: dict) -> list[ReactionEvent]:
        """
        处理一个事件，更新内部状态，返回反应事件列表。

        Args:
            event_description: 事件描述（中文）
            severity: 事件严重度 0-1
            source: 事件来源（agent 名字或 system）
            context: 环境上下文（包含 agents, turn 等信息）

        Returns:
            该层产生的反应事件列表
        """
        pass

    @abstractmethod
    def get_state(self) -> dict:
        """返回当前层状态的可序列化字典"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """返回中文描述，供 agent perceive 使用"""
        pass

    def reset(self) -> None:
        """重置层状态"""
        pass

    def decay(self) -> None:
        """每回合衰减（热度下降、情绪冷却等）"""
        pass
