# -*- coding: utf-8 -*-
"""
干预系统 - 用户 what-if 条件

支持在特定日期触发强制动作、注入外部事件、修改关系强度等。
"""

from __future__ import annotations

from swarmsim.crisis.models import InterventionCondition


class InterventionSystem:
    """用户干预条件系统"""

    def __init__(self):
        self.pending: list[InterventionCondition] = []
        self.applied: list[InterventionCondition] = []

    def add_intervention(self, condition: InterventionCondition) -> None:
        """添加干预条件"""
        self.pending.append(condition)

    def add_interventions(self, conditions: list[InterventionCondition]) -> None:
        for c in conditions:
            self.add_intervention(c)

    def check_interventions(
        self, current_day: int, current_state: dict | None = None
    ) -> list[InterventionCondition]:
        """检查并返回当天应触发的干预"""
        triggered = []
        remaining = []

        for cond in self.pending:
            should_fire = True

            if cond.day is not None and cond.day != current_day:
                should_fire = False

            if should_fire:
                triggered.append(cond)
                self.applied.append(cond)
            else:
                remaining.append(cond)

        self.pending = remaining
        return triggered

    def apply_intervention(
        self, condition: InterventionCondition, simulation: "CrisisSimulation"
    ) -> dict:
        """应用干预到仿真中

        Returns:
            干预效果描述
        """
        effects = {"description": condition.description}

        # 强制某人执行某动作
        if condition.person and condition.action:
            effects["forced_action"] = {
                "person": condition.person,
                "action": condition.action,
            }

        # 注入外部事件
        if condition.external_event:
            effects["injected_event"] = condition.external_event

        return effects

    def get_pending_descriptions(self) -> list[str]:
        return [c.description for c in self.pending]

    def get_applied_descriptions(self) -> list[str]:
        return [c.description for c in self.applied]

    def reset(self):
        self.pending.clear()
        self.applied.clear()
