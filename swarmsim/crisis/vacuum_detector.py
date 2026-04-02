# -*- coding: utf-8 -*-
"""
信息真空检测器 - 沉默导致谣言级联

当明星持续沉默时，信息真空被谣言和猜测性报道填补。
沉默越久，谣言越多、越离谱。
"""

from __future__ import annotations

import random
import re
import logging
from datetime import datetime
from typing import Any

from swarmsim.crisis.models import PRAction, CrisisAction

logger = logging.getLogger(__name__)


# ── 事件关键词 → 事件主题提取 ──
# 用于从场景描述中提取一个简短的"事件主题"标签，
# 供谣言模板引用，确保谣言始终围绕具体事件展开。

_TOPIC_RULES: list[tuple[list[str], str]] = [
    # (关键词, 主题标签) — 按优先级排列，越具体越靠前
    # 出轨/婚外情类（必须排在代言前面，避免"直播"误匹配）
    (["亲密互动", "出轨", "夜宿", "婚外情", "第三者"], "出轨"),
    # 虚假宣传/假洋品牌
    (["假洋品牌", "造假", "虚假宣传", "假冒"], "虚假宣传"),
    # 代言带货（排除单独的"直播"，避免误匹配）
    (["代言", "带货", "直播带货", "主播", "选品"], "代言带货"),
    (["吸毒", "毒品", "涉毒"], "涉毒"),
    (["偷税", "逃税", "税务", "阴阳合同"], "偷逃税"),
    (["离婚", "分手", "婚姻破裂"], "婚变"),
    (["封杀", "封禁", "下架"], "封杀"),
    (["抄袭", "剽窃"], "抄袭"),
    (["家暴", "施暴"], "家暴"),
]


def _extract_topic(description: str) -> str:
    """从场景描述中提取事件主题

    Returns:
        最多两个匹配的主题拼接，如 "代言带货/虚假宣传"
        无匹配时返回 "争议"
    """
    matched: list[str] = []
    for keywords, label in _TOPIC_RULES:
        if any(kw in description for kw in keywords):
            matched.append(label)
    if matched:
        # 最多取前两个，避免太长
        return "/".join(matched[:2])
    return "争议"


# ── 谣言套路（角度） ──
# 每个套路是一种谣言的"编造方向"，通过 {person} {target} {topic}
# 三个变量与具体事件绑定，确保内容始终相关。
#
# 角度说明：
#   escalation  — 事件比已知的更严重
#   coverup     — 当事人早就知道/在隐瞒
#   chain       — 牵连其他人
#   insider     — 利益内幕
#   digging     — 翻旧账

_RUMOR_ANGLES: dict[str, list[str]] = {
    "escalation": [
        "据传{person}的{topic}问题远比曝光的更严重",
        "知情人称这只是冰山一角，{person}的{topic}还有更多未公开的内幕",
        "据传这次{topic}事件的规模比想象中大得多",
        "有爆料称{person}在{topic}方面的问题不止这一次",
    ],
    "coverup": [
        "知情人爆料{person}早就知道{topic}的问题，但选择了隐瞒",
        "据传{person}团队正在紧急销毁{topic}相关证据",
        "有消息称{person}私下已就{topic}与相关方达成秘密协议",
        "据传{person}的道歉只是为了平息舆论，实际并未真正反思{topic}问题",
    ],
    "chain": [
        "网友质疑{person}的{topic}风波是否也牵连了{target}",
        "据传{target}也被卷入{person}的{topic}事件",
        "知情人称{topic}事件可能还涉及更多圈内人",
        "有消息称{person}和{target}在{topic}事件中是同一利益链条",
    ],
    "insider": [
        "圈内人士爆料{person}在{topic}事件中获利巨大",
        "据传{person}从{topic}中获得了{amount}的利益",
        "知情人称{person}的{topic}事件背后有精心策划的团队运作",
        "据传{person}在{topic}中的角色远不止表面看到的那么简单",
    ],
    "digging": [
        "网友挖出{person}过去在{topic}方面的更多问题",
        "据传{person}此前就因{topic}相关问题被内部警告过",
        "知情人称{person}的{topic}问题由来已久，只是这次被曝光了",
        "有人翻出{person}早年的言论，发现与{topic}事件的说法自相矛盾",
    ],
}

_ANGLE_WEIGHTS = {
    "escalation": 3,
    "coverup": 3,
    "chain": 2,
    "insider": 2,
    "digging": 2,
}

# ── 通用模板（最后兜底，引用事件标题） ──

_GENERIC_FALLBACK_TEMPLATES: list[str] = [
    "据传{person}正在秘密处理「{title}」相关事宜",
    "圈内人士爆料{person}因「{title}」事件情绪崩溃",
    "有消息称{person}准备就「{title}」事件退圈",
    "知情人称「{title}」事件还有更多当事人即将站出来",
    "据传相关部门已经就「{title}」介入调查",
]


def generate_rumor(
    person: str,
    target: str,
    scenario_description: str,
    scenario_title: str = "",
) -> str:
    """根据具体事件生成上下文相关的谣言

    核心逻辑：从场景描述提取事件主题，结合谣言角度（升级/隐瞒/连锁/内幕/翻旧账），
    生成始终围绕具体事件的谣言。

    Args:
        person: 谣言主角
        target: 谣言中可能牵连的其他人
        scenario_description: 场景描述（事件的详细内容）
        scenario_title: 场景标题

    Returns:
        生成的谣言文本
    """
    topic = _extract_topic(scenario_description)

    # 按权重随机选一个谣言角度
    angles = list(_ANGLE_WEIGHTS.keys())
    weights = [_ANGLE_WEIGHTS[a] for a in angles]
    angle = random.choices(angles, weights=weights, k=1)[0]
    template = random.choice(_RUMOR_ANGLES[angle])

    # 随机金额
    amount = random.choice(["数百万", "上千万", "数千万", "百万级", "天价"])

    return template.format(
        person=person,
        target=target,
        topic=topic,
        amount=amount,
    )


# ── 向后兼容 ──
# RUMOR_TEMPLATES 保留给 LLM content generator 作为 fallback，
# 但 rule 模式下不再使用它。谣言生成统一走 generate_rumor()。

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
        "据说{person}对孩子的抚养权问题态度强硬",
        "有消息称{person}要求高额财产分割",
    ],
    "scandal": [
        "圈内人士爆料{person}的{topic}问题远比曝光的更严重",
        "知情人称{person}在{topic}方面的内幕还有更多",
        "网友质疑{person}的{topic}事件是否牵连了{target}",
        "据传{person}从{topic}中获利巨大",
        "据传相关部门已经就{person}的{topic}问题介入调查",
    ],
    "other": [
        "据传{person}正在秘密处理此事",
        "圈内人士爆料{person}最近情绪崩溃",
        "有消息称{person}准备退圈",
    ],
}


class InformationVacuumDetector:
    """信息真空检测器"""

    def __init__(self, content_generator: Any | None = None,
                 scenario_description: str = "",
                 scenario_title: str = ""):
        self.silence_days: dict[str, int] = {}    # person → 连续沉默天数
        self.generated_rumors: list[dict] = []
        self._content_gen = content_generator
        self._scenario_description = scenario_description
        self._scenario_title = scenario_title

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
            gossip_type: 八卦类型（仅供 LLM 模式使用）

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

            # 随机选择 target
            others = [p for p in involved_persons if p != person]
            target = random.choice(others) if others else "相关人员"

            # 计算严重度
            severity = min(0.9, 0.3 + days_silent * 0.1)

            # 生成谣言内容 — 三级优先：LLM > 事件上下文 > 通用兜底
            content = None

            if self._content_gen:
                try:
                    ctx = {
                        "gossip_type": gossip_type,
                        "person": person,
                        "target": target,
                        "days_silent": days_silent,
                        "severity": severity,
                    }
                    if self._scenario_description:
                        ctx["scenario_description"] = self._scenario_description
                    if self._scenario_title:
                        ctx["scenario_title"] = self._scenario_title
                    content = self._content_gen.generate(ctx)
                except Exception as e:
                    logger.warning(f"ContentGen 谣言生成失败: {e}，回退模板")
                    content = None

            if content is None and self._scenario_description:
                content = generate_rumor(
                    person=person,
                    target=target,
                    scenario_description=self._scenario_description,
                    scenario_title=self._scenario_title,
                )

            if content is None:
                # 最终兜底：至少引用事件标题
                title = self._scenario_title or "此事"
                template = random.choice(_GENERIC_FALLBACK_TEMPLATES)
                content = template.format(person=person, title=title)

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
