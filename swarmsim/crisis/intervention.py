# -*- coding: utf-8 -*-
"""
干预系统 - 用户 what-if 条件

支持三种触发类型：定时、相对天数、状态阈值。
支持三种动作类型：强制动作、注入外部事件、关系变更。
"""

from __future__ import annotations

import random

from swarmsim.crisis.models import (
    InterventionCondition, ExternalEventType,
    TrendingTopic, MediaHeadline,
)


# ── 外部事件效果模板 ──

EVENT_TYPE_EFFECTS: dict[str, dict] = {
    ExternalEventType.MEDIA_REPORT: {
        "approval_delta": -5,
        "heat_delta": 15,
        "brand_delta": -3,
        "description": "权威媒体发布深度报道",
    },
    ExternalEventType.VIDEO_LEAK: {
        "approval_delta": -10,
        "heat_delta": 25,
        "brand_delta": -5,
        "description": "关键视频/录音被泄露",
    },
    ExternalEventType.COMPETITOR_ANNOUNCE: {
        "approval_delta": -3,
        "heat_delta": 10,
        "brand_delta": -2,
        "description": "竞争对手发表声明",
    },
    ExternalEventType.REGULATORY_ACTION: {
        "approval_delta": -8,
        "heat_delta": 20,
        "brand_delta": -6,
        "description": "监管部门介入",
    },
    ExternalEventType.BRAND_DECISION: {
        "approval_delta": -4,
        "heat_delta": 8,
        "brand_delta": -8,
        "description": "重要品牌做出决策",
    },
    ExternalEventType.CUSTOM: {
        "approval_delta": -5,
        "heat_delta": 10,
        "brand_delta": -3,
        "description": "自定义外部事件",
    },
}


class InterventionSystem:
    """用户干预条件系统"""

    def __init__(self):
        self.pending: list[InterventionCondition] = []
        self.applied: list[InterventionCondition] = []
        self._start_day: int | None = None  # 用于相对天数计算

    def add_intervention(self, condition: InterventionCondition) -> None:
        """添加干预条件"""
        self.pending.append(condition)

    def add_interventions(self, conditions: list[InterventionCondition]) -> None:
        for c in conditions:
            self.add_intervention(c)

    def set_start_day(self, day: int) -> None:
        """设置仿真开始日期（用于相对天数计算）"""
        self._start_day = day

    def check_interventions(
        self, current_day: int, current_state: dict | None = None
    ) -> list[InterventionCondition]:
        """检查并返回当天应触发的干预

        支持三种触发类型：
        - time_absolute: 在指定绝对日期触发
        - time_relative: 在仿真开始后 N 天触发
        - state_threshold: 当某个指标达到阈值时触发
        """
        current_state = current_state or {}
        triggered = []
        remaining = []

        for cond in self.pending:
            should_fire = False

            trigger_type = getattr(cond, "trigger_type", "time_absolute")

            if trigger_type == "time_absolute":
                # 原有逻辑：精确匹配日期
                if cond.day is not None and cond.day == current_day:
                    should_fire = True
                elif cond.day is None:
                    # 无日期限制，总是触发
                    should_fire = True

            elif trigger_type == "time_relative":
                # 相对天数：从仿真开始后第 N 天
                if cond.day is not None and self._start_day is not None:
                    target_day = self._start_day + cond.day
                    if current_day >= target_day:
                        should_fire = True
                elif cond.day is not None and self._start_day is None:
                    # 没有设置开始日期，退化为绝对天数
                    if cond.day == current_day:
                        should_fire = True

            elif trigger_type == "state_threshold":
                # 状态阈值触发
                should_fire = self._check_threshold(cond, current_state)

            if should_fire:
                triggered.append(cond)
                self.applied.append(cond)
            else:
                remaining.append(cond)

        self.pending = remaining
        return triggered

    def _check_threshold(
        self, cond: InterventionCondition, state: dict
    ) -> bool:
        """检查状态阈值条件"""
        metric = cond.metric
        threshold = cond.threshold
        comparator = cond.comparator or "lt"

        if metric is None or threshold is None:
            return False

        # 获取当前值
        current_value = self._get_metric_value(metric, cond.person, state)
        if current_value is None:
            return False

        # 比较
        if comparator == "lt":
            return current_value < threshold
        elif comparator == "gt":
            return current_value > threshold
        elif comparator == "lte":
            return current_value <= threshold
        elif comparator == "gte":
            return current_value >= threshold
        return False

    @staticmethod
    def _get_metric_value(
        metric: str, person: str | None, state: dict
    ) -> float | None:
        """从状态中获取指标值"""
        if metric == "approval":
            if person and person in state.get("approval_scores", {}):
                return state["approval_scores"][person]
            # 如果没指定人，用平均口碑
            scores = state.get("approval_scores", {})
            if scores:
                return sum(scores.values()) / len(scores)
        elif metric == "heat":
            return state.get("heat_index")
        elif metric == "brand":
            if person and person in state.get("brand_values", {}):
                return state["brand_values"][person]
            values = state.get("brand_values", {})
            if values:
                return sum(values.values()) / len(values)
        elif metric == "regulatory":
            return float(state.get("regulatory_level", 0))
        return None

    def apply_intervention(
        self, condition: InterventionCondition, simulation: "CrisisSimulation"
    ) -> dict:
        """应用干预到仿真中

        支持三种动作：
        1. 强制动作：指定人执行指定 PR 动作
        2. 外部事件：注入事件影响热度/口碑
        3. 关系变更：修改两人间关系强度
        """
        effects = {"description": condition.description}

        # 1. 强制某人执行某动作
        if condition.person and condition.action:
            effects["forced_action"] = {
                "person": condition.person,
                "action": condition.action,
            }

        # 2. 注入外部事件
        if condition.external_event or condition.event_type:
            event_effects = self._apply_event_type(condition, simulation)
            effects.update(event_effects)

        # 3. 关系变更
        if condition.person_a and condition.person_b and condition.relationship_change:
            rel_effects = self._apply_relationship_change(condition, simulation)
            effects.update(rel_effects)

        return effects

    def _apply_event_type(
        self, cond: InterventionCondition, simulation: "CrisisSimulation"
    ) -> dict:
        """按事件类型计算并应用效果"""
        event_type_str = cond.event_type or "custom"
        try:
            event_type = ExternalEventType(event_type_str)
        except ValueError:
            event_type = ExternalEventType.CUSTOM

        template = EVENT_TYPE_EFFECTS.get(event_type, EVENT_TYPE_EFFECTS[ExternalEventType.CUSTOM])

        # 目标人物（如果有指定，否则影响所有人）
        target_person = cond.person
        severity_mult = 1.0

        # 应用效果到仿真状态
        approval_delta = template["approval_delta"] * severity_mult
        heat_delta = template["heat_delta"] * severity_mult
        brand_delta = template["brand_delta"] * severity_mult

        if target_person and target_person in simulation.current_state.approval_scores:
            simulation.current_state.approval_scores[target_person] = max(
                0, min(100,
                    simulation.current_state.approval_scores[target_person] + approval_delta
                )
            )
            if target_person in simulation.current_state.brand_values:
                simulation.current_state.brand_values[target_person] = max(
                    0, min(100,
                        simulation.current_state.brand_values[target_person] + brand_delta
                    )
                )
        else:
            # 影响所有人
            for name in simulation.current_state.approval_scores:
                simulation.current_state.approval_scores[name] = max(
                    0, min(100,
                        simulation.current_state.approval_scores[name] + approval_delta * 0.5
                    )
                )
            for name in simulation.current_state.brand_values:
                simulation.current_state.brand_values[name] = max(
                    0, min(100,
                        simulation.current_state.brand_values[name] + brand_delta * 0.5
                    )
                )

        simulation.current_state.heat_index = min(
            100, simulation.current_state.heat_index + heat_delta
        )

        # 生成配套热搜和媒体
        event_desc = cond.external_event or template["description"]
        person_label = target_person or "当事人"

        simulation.current_state.trending_topics.insert(0, TrendingTopic(
            rank=1,
            title=f"[外部事件] {event_desc}",
            heat=simulation.current_state.heat_index,
            category="突发事件",
        ))
        simulation.current_state.media_headlines.insert(0, MediaHeadline(
            outlet="突发新闻",
            headline=event_desc,
            sentiment="negative",
            reach=0.9,
        ))

        return {
            "injected_event": event_desc,
            "event_type": event_type_str,
            "approval_delta": approval_delta,
            "heat_delta": heat_delta,
            "brand_delta": brand_delta,
        }

    def _apply_relationship_change(
        self, cond: InterventionCondition, simulation: "CrisisSimulation"
    ) -> dict:
        """修改两人间关系"""
        name_a = cond.person_a
        name_b = cond.person_b
        change_type = cond.relationship_change or "strengthen"

        # 查找并修改知识图谱中的关系
        kg = simulation.kg
        node_a = f"celebrity:{name_a}"
        node_b = f"celebrity:{name_b}"

        changed = False
        if kg._graph.has_node(node_a) and kg._graph.has_node(node_b):
            # 查找现有的关系边
            edges_to_update = []
            if kg._graph.has_edge(node_a, node_b):
                for key, data in kg._graph[node_a][node_b].items():
                    edges_to_update.append((node_a, node_b, key, data))
            if kg._graph.has_edge(node_b, node_a):
                for key, data in kg._graph[node_b][node_a].items():
                    edges_to_update.append((node_b, node_a, key, data))

            for src, tgt, key, data in edges_to_update:
                if change_type == "strengthen":
                    data["strength"] = min(1.0, data.get("strength", 0.5) + 0.2)
                    changed = True
                elif change_type == "weaken":
                    data["strength"] = max(0.0, data.get("strength", 0.5) - 0.2)
                    changed = True
                elif change_type == "break":
                    data["strength"] = 0.05
                    data["confidence"] = 0.1
                    changed = True

            # 新建关系
            if change_type == "new" and not edges_to_update:
                kg._graph.add_edge(
                    node_a, node_b,
                    edge_type="relationship",
                    relation_type="自定义",
                    strength=0.5,
                    confidence=0.3,
                    source="intervention",
                )
                changed = True

        effect_desc = {
            "strengthen": "关系加强",
            "weaken": "关系减弱",
            "break": "关系断裂",
            "new": "建立新关系",
        }.get(change_type, change_type)

        # 关系变更本身也会产生热度
        if changed:
            simulation.current_state.heat_index = min(
                100, simulation.current_state.heat_index + 5
            )

        return {
            "relationship_change": {
                "person_a": name_a,
                "person_b": name_b,
                "change_type": change_type,
                "result": effect_desc if changed else "未找到关系",
            }
        }

    def get_pending_descriptions(self) -> list[str]:
        descs = []
        for c in self.pending:
            parts = []
            trigger_type = getattr(c, "trigger_type", "time_absolute")

            # 触发类型
            if trigger_type == "state_threshold":
                metric_label = {
                    "approval": "口碑", "heat": "热度",
                    "brand": "品牌", "regulatory": "监管",
                }.get(c.metric or "", c.metric or "")
                comp_label = {
                    "lt": "<", "gt": ">", "lte": "<=", "gte": ">=",
                }.get(c.comparator or "", "")
                parts.append(f"当{metric_label}{comp_label}{c.threshold}")
            elif trigger_type == "time_relative":
                parts.append(f"开始后第{c.day}天")
            elif c.day is not None:
                parts.append(f"第{c.day}天")

            if c.description:
                parts.append(c.description)

            # 动作类型
            if c.person and c.action:
                action_label = {
                    "silence": "沉默", "apologize": "道歉",
                    "statement": "声明", "go_on_show": "上节目",
                    "lawsuit": "起诉", "hide": "隐退",
                    "play_victim": "卖惨", "counterattack": "反击",
                    "charity": "公益", "comeback": "复出",
                }.get(c.action, c.action)
                parts.append(f"{c.person}→{action_label}")

            if c.external_event or c.event_type:
                etype_label = {
                    "media_report": "媒体报道", "video_leak": "视频泄露",
                    "competitor_announce": "对手声明", "regulatory_action": "监管行动",
                    "brand_decision": "品牌决策", "custom": "自定义",
                }.get(c.event_type or "custom", "事件")
                parts.append(f"[{etype_label}]{c.external_event or ''}")

            if c.person_a and c.person_b and c.relationship_change:
                change_label = {
                    "strengthen": "↑", "weaken": "↓",
                    "break": "✗", "new": "+",
                }.get(c.relationship_change, c.relationship_change)
                parts.append(f"{c.person_a}{change_label}{c.person_b}")

            descs.append(" | ".join(parts) if parts else "干预")
        return descs

    def get_applied_descriptions(self) -> list[str]:
        return [c.description for c in self.applied]

    def reset(self):
        self.pending.clear()
        self.applied.clear()
        self._start_day = None
