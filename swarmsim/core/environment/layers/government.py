# -*- coding: utf-8 -*-
"""
政府监管层 - 关键词审查、监管警告、封禁
"""

from __future__ import annotations

from ..models import (
    ReactionEvent, RegulatoryState,
    RegulatoryAction
)
from .base import ReactionLayer


# 敏感词分级
SENSITIVE_KEYWORDS = {
    # level 1: 轻微 - 关键词屏蔽
    1: ["不专业", "耍大牌", "迟到", "罢录", "耍脾气", "态度差"],
    # level 2: 中度 - 内容下架
    2: ["出轨", "劈腿", "偷情", "婚外情", "小三", "夜会"],
    # level 3: 严重 - 限流
    3: ["吸毒", "赌博", "涉黑", "暴力", "家暴", "偷税", "逃税"],
    # level 4: 极重 - 官方警告
    4: ["卖淫", "嫖娼", "性侵", "强奸", "非法集资"],
    # level 5: 封禁
    5: ["分裂国家", "政治敏感"],
}

# 监管措施文本
ACTION_TEXTS = {
    RegulatoryAction.KEYWORD_WARNING: "相关话题已被平台标记，搜索结果受限",
    RegulatoryAction.CONTENT_REMOVAL: "涉事内容已被要求下架",
    RegulatoryAction.ACCOUNT_RESTRICTION: "相关账号已被限流处理",
    RegulatoryAction.OFFICIAL_WARNING: "广电总局约谈相关经纪公司",
    RegulatoryAction.TEMPORARY_BAN: "涉事艺人被临时禁言，作品暂停播出",
    RegulatoryAction.PERMANENT_BAN: "涉事艺人被列为劣迹艺人，永久封禁",
}


class GovernmentLayer(ReactionLayer):
    """政府/监管反应层"""

    layer_name = "government"

    def __init__(self):
        self.state = RegulatoryState()
        self.agent_escalation: dict[str, int] = {}      # agent_id -> 0-5
        self.agent_actions: dict[str, RegulatoryAction] = {}
        self.action_history: list[str] = []

    def register_agent(self, agent_id: str):
        self.agent_escalation[agent_id] = 0
        self.agent_actions[agent_id] = RegulatoryAction.NONE

    def react(self, event_description: str, severity: float,
              source: str, context: dict) -> list[ReactionEvent]:
        reactions = []

        # 扫描关键词
        triggered_level = self._scan_keywords(event_description)

        if triggered_level == 0:
            return reactions

        self.state.triggered_keywords.append(
            self._get_triggered_word(event_description, triggered_level)
        )

        # 确定涉事 agent
        target_ids = []
        agents = context.get("agents", {})
        for aid, agent in agents.items():
            name = getattr(agent, "config", None)
            if name:
                name = getattr(name, "name", str(agent))
            else:
                name = str(agent)
            if name in event_description or source in str(agent):
                target_ids.append(aid)
                # 累加升级
                self.agent_escalation[aid] = max(
                    self.agent_escalation.get(aid, 0) + triggered_level,
                    5
                )

        # 决定监管措施
        action = self._determine_action(triggered_level, severity)
        if action != RegulatoryAction.NONE:
            self.state.action = action
            self.state.warning_text = ACTION_TEXTS.get(action, "")
            self.state.affected_agent_ids = target_ids
            self.state.escalation_level = triggered_level

            for aid in target_ids:
                self.agent_actions[aid] = action

            self.action_history.append(f"[{action.value}] {self.state.warning_text}")

            reactions.append(ReactionEvent(
                source_event_id=context.get("event_id", ""),
                reaction_layer=self.layer_name,
                severity=float(triggered_level) / 5,
                target_agent_ids=target_ids,
                description=f"监管措施: {self.state.warning_text}",
                metadata={"action": action.value, "level": triggered_level},
            ))

        return reactions

    def _scan_keywords(self, text: str) -> int:
        """扫描关键词，返回触发级别（0=未触发）"""
        max_level = 0
        for level, keywords in SENSITIVE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    max_level = max(max_level, level)
        return max_level

    def _get_triggered_word(self, text: str, level: int) -> str:
        """获取触发的关键词"""
        for kw in SENSITIVE_KEYWORDS.get(level, []):
            if kw in text:
                return kw
        return ""

    def _determine_action(self, level: int, severity: float) -> RegulatoryAction:
        """根据级别决定监管措施"""
        action_map = {
            1: RegulatoryAction.KEYWORD_WARNING,
            2: RegulatoryAction.CONTENT_REMOVAL,
            3: RegulatoryAction.ACCOUNT_RESTRICTION,
            4: RegulatoryAction.OFFICIAL_WARNING,
            5: RegulatoryAction.TEMPORARY_BAN if severity < 0.9 else RegulatoryAction.PERMANENT_BAN,
        }
        return action_map.get(level, RegulatoryAction.NONE)

    def decay(self):
        """审查关键词过期"""
        if len(self.state.triggered_keywords) > 10:
            self.state.triggered_keywords = self.state.triggered_keywords[-10:]

    def get_state(self) -> dict:
        return {
            "current_action": self.state.action.value,
            "escalation_level": self.state.escalation_level,
            "triggered_keywords": self.state.triggered_keywords[-5:],
            "action_history": self.action_history[-5:],
        }

    def get_description(self) -> str:
        lines = ["【政府监管】"]
        if self.state.action != RegulatoryAction.NONE:
            lines.append(f"  当前措施: {self.state.action.value}")
            lines.append(f"  {self.state.warning_text}")
        else:
            lines.append("  暂无监管动作")
        if self.state.triggered_keywords:
            lines.append(f"  已触发关键词: {', '.join(self.state.triggered_keywords[-3:])}")
        return "\n".join(lines)

    def reset(self):
        self.state = RegulatoryState()
        self.action_history.clear()
        for aid in self.agent_escalation:
            self.agent_escalation[aid] = 0
            self.agent_actions[aid] = RegulatoryAction.NONE
