# -*- coding: utf-8 -*-
"""
综艺节目专用环境

添加任务系统、预算限制等综艺节目特有的机制。
"""

from __future__ import annotations

import random
from datetime import timedelta

from .base import Environment


class VarietyShowEnvironment(Environment):
    """综艺节目专用环境"""

    def __init__(
        self,
        name: str = "综艺修罗场",
        initial_budget: float = 1000.0,
        task_complexity: float = 0.5,
    ):
        super().__init__(name=name)
        self.budget = initial_budget
        self.initial_budget = initial_budget
        self.task_complexity = task_complexity
        self.current_task = ""
        self.task_deadline = None

        # 综艺特有属性
        self.camera_on = False
        self.screen_time: dict[str, int] = {}

    def set_task(self, task: str, deadline_hours: int = 24) -> None:
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
                severity=0.3,
            )
            return True
        else:
            self.broadcast(
                f"预算不足！当前剩余: {self.budget}",
                source="system",
                importance=0.8,
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
        return sorted(self.screen_time.items(), key=lambda x: x[1], reverse=True)

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
录制状态: {'录制中' if self.camera_on else '未录制'}
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
