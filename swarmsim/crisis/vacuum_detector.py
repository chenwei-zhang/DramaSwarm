# -*- coding: utf-8 -*-
"""
信息真空检测器 - 沉默导致谣言级联

当明星持续沉默时，信息真空被谣言和猜测性报道填补。
沉默越久，谣言越多、越离谱。
"""

from __future__ import annotations

import random
from datetime import datetime

from swarmsim.crisis.models import PRAction, CrisisAction


# ── 谣言模板 ──

RUMOR_TEMPLATES: dict[str, list[str]] = {
    "cheating": [
        "据知情人透露，{person}其实还有第三者...",
        "网友扒出{person}与神秘人同进酒店照片",
        "据传{person}给了{target}巨额封口费",
        "有爆料称{person}和{target}早已暗中来往半年",
        "圈内人士称{person}不是第一次了",
    ],
    "divorce": [
        "据传两人早已秘密签署离婚协议",
        "知情人爆料{person}已搬出共同住所",
        "据说孩子抚养权争夺激烈",
        "有消息称{person}要求天价分手费",
    ],
    "scandal": [
        "圈内人士爆料{person}背后还有更大的瓜",
        "据说这次只是冰山一角",
        "网友挖出{person}更多黑历史",
        "知情人称有更多当事人即将站出来",
        "据传相关部门已经介入调查",
    ],
    "other": [
        "据传{person}正在秘密处理此事",
        "圈内人士爆料{person}最近情绪崩溃",
        "有消息称{person}准备退圈",
    ],
}


class InformationVacuumDetector:
    """信息真空检测器"""

    def __init__(self):
        self.silence_days: dict[str, int] = {}    # person → 连续沉默天数
        self.generated_rumors: list[dict] = []

    def update(
        self,
        day: int,
        day_actions: list[CrisisAction],
        involved_persons: list[str],
        gossip_type: str = "scandal",
    ) -> list[dict]:
        """追踪沉默并生成谣言

        Args:
            day: 当前天数
            day_actions: 当天的公关动作
            involved_persons: 涉及的人物
            gossip_type: 八卦类型

        Returns:
            新生成的谣言列表
        """
        new_rumors = []

        # 统计每人当天是否有动作
        actors_with_action: set[str] = set()
        for action in day_actions:
            if action.action not in (PRAction.SILENCE, PRAction.HIDE):
                actors_with_action.add(action.actor)

        # 更新沉默计数
        for person in involved_persons:
            if person in actors_with_action:
                self.silence_days[person] = 0
            else:
                self.silence_days[person] = self.silence_days.get(person, 0) + 1

        # 根据沉默天数生成谣言
        for person in involved_persons:
            days_silent = self.silence_days.get(person, 0)

            if days_silent < 2:
                continue

            # 概率递增：2天30%，3天50%，4天+70%
            if days_silent == 2:
                prob = 0.3
            elif days_silent == 3:
                prob = 0.5
            else:
                prob = min(0.9, 0.5 + (days_silent - 3) * 0.1)

            if random.random() > prob:
                continue

            # 从模板池选择谣言
            templates = RUMOR_TEMPLATES.get(
                gossip_type, RUMOR_TEMPLATES["other"]
            )
            template = random.choice(templates)

            # 随机选择 target
            others = [p for p in involved_persons if p != person]
            target = random.choice(others) if others else "相关人员"

            content = template.format(person=person, target=target)
            severity = min(0.9, 0.3 + days_silent * 0.1)

            rumor = {
                "day": day,
                "person": person,
                "content": content,
                "severity": round(severity, 2),
                "source": "网络爆料",
                "verified": False,
            }
            new_rumors.append(rumor)
            self.generated_rumors.append(rumor)

        return new_rumors

    def get_rumor_impact(self, rumor: dict) -> dict:
        """谣言对指标的影响"""
        return {
            "approval_delta": round(-rumor["severity"] * 8, 1),
            "heat_delta": round(rumor["severity"] * 15, 1),
            "rumor_count_delta": 1,
        }

    def try_debunk(
        self,
        person: str,
        action_type: str,
        day: int,
    ) -> list[dict]:
        """尝试辟谣已生成的谣言

        当 Agent 执行 STATEMENT/LAWSUIT 等主动回应动作时调用。
        辟谣概率取决于动作类型：STATEMENT 40%, LAWSUIT 60%, GO_ON_SHOW 50%

        Args:
            person: 辟谣的人
            action_type: 动作类型（PRAction.value）
            day: 当前天数

        Returns:
            被辟谣的谣言列表
        """
        debunk_chances = {
            "statement": 0.4,
            "go_on_show": 0.5,
            "lawsuit": 0.6,
            "counterattack": 0.3,
        }
        chance = debunk_chances.get(action_type, 0.2)

        debunked = []
        for rumor in self.generated_rumors:
            if rumor.get("debunked"):
                continue
            if rumor.get("person") != person:
                continue
            if random.random() < chance:
                rumor["debunked"] = True
                rumor["debunked_day"] = day
                rumor["severity"] = max(0.05, rumor["severity"] * 0.2)
                debunked.append(rumor)

        return debunked

    def get_silence_status(self) -> dict[str, int]:
        return dict(self.silence_days)

    def reset(self):
        self.silence_days.clear()
        self.generated_rumors.clear()
