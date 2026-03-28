# -*- coding: utf-8 -*-
"""
Agent 间消息总线

每轮仿真日内，管理 celebrity agent 和 audience agent 之间的消息传递。
"""

from __future__ import annotations

from swarmsim.crisis.models import AgentMessage


class MessageBus:
    """轻量消息总线，每 simulation day 内有效"""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []

    def broadcast(self, msg: AgentMessage) -> None:
        """广播消息给所有 Agent"""
        msg.receiver = None
        self._messages.append(msg)

    def broadcast_list(self, msgs: list[AgentMessage]) -> None:
        """批量广播"""
        for m in msgs:
            m.receiver = None
        self._messages.extend(msgs)

    def send_to(self, person: str, msg: AgentMessage) -> None:
        """定向发送"""
        msg.receiver = person
        self._messages.append(msg)

    def get_messages(self, person: str) -> list[AgentMessage]:
        """获取发给某人或广播的消息"""
        return [
            m for m in self._messages
            if m.receiver is None or m.receiver == person
        ]

    def get_audience_reactions(self) -> list[AgentMessage]:
        """获取观众来源的消息"""
        return [m for m in self._messages if m.source == "audience"]

    def get_celebrity_messages(self) -> list[AgentMessage]:
        """获取明星来源的消息"""
        return [m for m in self._messages if m.source == "celebrity"]

    def clear(self) -> None:
        """每日清空"""
        self._messages.clear()
