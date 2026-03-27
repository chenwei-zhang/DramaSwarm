# -*- coding: utf-8 -*-
"""
公众舆论层 - 网民情绪、粉丝反应、好感度
"""

from __future__ import annotations

import random

from ..models import (
    ReactionEvent, NetizenSentiment, FanReaction,
    SentimentPolarity, FanReactionType
)
from .base import ReactionLayer


# 事件关键词 → 情绪影响
NEGATIVE_KEYWORDS = {
    "出轨": 0.8, "劈腿": 0.75, "偷情": 0.8, "家暴": 0.9,
    "偷税": 0.85, "吸毒": 0.9, "封杀": 0.7, "劣迹": 0.7,
    "离婚": 0.5, "分手": 0.4, "撕逼": 0.6, "互撕": 0.6,
    "造假": 0.65, "欺骗": 0.6, "撒谎": 0.55, "耍大牌": 0.45,
    "不专业": 0.35, "争议": 0.4, "批评": 0.35, "道歉": 0.3,
    "怒怼": 0.5, "嘲讽": 0.45, "翻车": 0.55, "塌房": 0.7,
}

POSITIVE_KEYWORDS = {
    "获奖": -0.3, "公益": -0.25, "捐款": -0.3, "努力": -0.2,
    "实力": -0.25, "好评": -0.3, "冠军": -0.35, "突破": -0.2,
    "感动": -0.25, "暖心": -0.2, "正能量": -0.3,
}

FAN_COMMENTS = {
    FanReactionType.SUPPORTIVE: [
        "永远支持{idol}！加油！",
        "{idol}最棒了，一直都在！",
        "不管怎样都喜欢你！",
    ],
    FanReactionType.DEFENSIVE: [
        "别黑{idol}了，你们根本不了解真相！",
        "{idol}是被冤枉的，大家理性看待！",
        "造谣可耻！支持{idol}维权！",
    ],
    FanReactionType.ANGRY: [
        "太过分了！{idol}凭什么受这种委屈！",
        "键盘侠别太过分！",
        "心疼{idol}，不想看了",
    ],
    FanReactionType.DISAPPOINTED: [
        "粉了这么多年，真的很失望",
        "脱粉了，再见",
        "曾经那么喜欢你，没想到你是这样的人",
    ],
    FanReactionType.MELON_EATING: [
        "又有瓜吃了，前排围观",
        "这事跟我无关，纯吃瓜",
        "娱乐圈就这样吧",
    ],
}

ANTI_FAN_COMMENTS = [
    "早就知道{idol}不是好东西",
    "活该，报应来了",
    "请彻底退出娱乐圈！",
    "{idol}的粉丝别洗了，事实摆在眼前",
]


class PublicOpinionLayer(ReactionLayer):
    """公众舆论反应层"""

    layer_name = "public_opinion"

    def __init__(self):
        self.agent_approval: dict[str, float] = {}       # agent_id -> 0-100
        self.agent_names: dict[str, str] = {}             # agent_id -> name
        self.sentiment_history: list[NetizenSentiment] = []
        self.current_sentiment = NetizenSentiment()
        self.heat_index: float = 0.0
        self.pending_fan_reactions: list[FanReaction] = []

    def register_agent(self, agent_id: str, name: str, initial_approval: float = 60.0):
        """注册一个明星到舆论追踪"""
        self.agent_approval[agent_id] = initial_approval
        self.agent_names[agent_id] = name

    def react(self, event_description: str, severity: float,
              source: str, context: dict) -> list[ReactionEvent]:
        reactions = []

        # 计算情绪偏移
        sentiment_shift = self._calc_sentiment_shift(event_description, severity)
        self._update_sentiment(sentiment_shift)

        # 更新热度
        self.heat_index = min(100, self.heat_index + severity * 30)

        # 更新涉及明星的好感度
        target_agents = self._find_involved_agents(event_description)
        for agent_id in target_agents:
            if agent_id in self.agent_approval:
                old_score = self.agent_approval[agent_id]
                delta = sentiment_shift * 20  # 放大影响
                new_score = max(0, min(100, old_score + delta))
                self.agent_approval[agent_id] = new_score

                # 生成粉丝反应
                fan = self._generate_fan_reaction(agent_id, new_score, old_score, event_description)
                if fan:
                    self.pending_fan_reactions.append(fan)
                    reactions.append(ReactionEvent(
                        source_event_id=context.get("event_id", ""),
                        reaction_layer=self.layer_name,
                        severity=abs(delta) / 20,
                        target_agent_ids=[agent_id],
                        description=f"粉丝反应({fan.reaction_type.value}): "
                                    + (fan.sample_comments[0] if fan.sample_comments else ""),
                    ))

        # 生成路人反应
        if abs(sentiment_shift) > 0.1:
            polarity = "负面" if sentiment_shift > 0 else "正面"
            reactions.append(ReactionEvent(
                source_event_id=context.get("event_id", ""),
                reaction_layer=self.layer_name,
                severity=self.heat_index / 100,
                target_agent_ids=[],
                description=f"网友{polarity}情绪升温，当前热度指数: {self.heat_index:.0f}/100",
            ))

        # 更新投票
        self._update_poll_scores()

        # 保存情绪快照
        self._snapshot_sentiment(context.get("turn", 0))

        return reactions

    def _calc_sentiment_shift(self, text: str, severity: float) -> float:
        """计算情绪偏移（正=负面恶化）"""
        shift = 0.0
        for kw, weight in NEGATIVE_KEYWORDS.items():
            if kw in text:
                shift += weight * severity
        for kw, weight in POSITIVE_KEYWORDS.items():
            if kw in text:
                shift += weight * severity  # weight是负值
        return max(-0.5, min(0.5, shift))

    def _update_sentiment(self, shift: float):
        """更新整体情绪"""
        if shift > 0:  # 负面
            self.current_sentiment.negative_ratio = min(0.8, self.current_sentiment.negative_ratio + shift)
            self.current_sentiment.positive_ratio = max(0.1, self.current_sentiment.positive_ratio - shift * 0.5)
        else:  # 正面
            self.current_sentiment.positive_ratio = min(0.8, self.current_sentiment.positive_ratio - shift)
            self.current_sentiment.negative_ratio = max(0.1, self.current_sentiment.negative_ratio + shift * 0.3)
        self.current_sentiment.neutral_ratio = max(0.05, 1 - self.current_sentiment.positive_ratio - self.current_sentiment.negative_ratio)

        if self.current_sentiment.negative_ratio > 0.5:
            self.current_sentiment.overall_polarity = SentimentPolarity.NEGATIVE
        elif self.current_sentiment.positive_ratio > 0.5:
            self.current_sentiment.overall_polarity = SentimentPolarity.POSITIVE
        else:
            self.current_sentiment.overall_polarity = SentimentPolarity.MIXED

    def _find_involved_agents(self, text: str) -> list[str]:
        """从文本中找到涉及的明星"""
        involved = []
        for agent_id, name in self.agent_names.items():
            if name in text:
                involved.append(agent_id)
        return involved

    def _generate_fan_reaction(self, agent_id: str, new_score: float,
                                old_score: float, text: str) -> FanReaction | None:
        """生成粉丝反应"""
        name = self.agent_names.get(agent_id, "")
        delta = new_score - old_score
        intensity = min(1.0, abs(delta) / 30)

        if delta <= -20:
            reaction_type = FanReactionType.DISAPPOINTED
        elif delta <= -10:
            reaction_type = FanReactionType.DEFENSIVE
        elif delta <= 0:
            reaction_type = FanReactionType.ANGRY
        elif delta >= 10:
            reaction_type = FanReactionType.SUPPORTIVE
        else:
            reaction_type = random.choice([
                FanReactionType.SUPPORTIVE, FanReactionType.MELON_EATING
            ])

        comments = []
        templates = FAN_COMMENTS.get(reaction_type, FAN_COMMENTS[FanReactionType.MELON_EATING])
        for t in random.sample(templates, min(2, len(templates))):
            comments.append(t.format(idol=name))

        return FanReaction(
            agent_name=name,
            reaction_type=reaction_type,
            intensity=intensity,
            sample_comments=comments,
        )

    def _update_poll_scores(self):
        """更新好感度到sentiment的poll_scores"""
        self.current_sentiment.poll_scores = {
            name: self.agent_approval[aid]
            for aid, name in self.agent_names.items()
        }

    def _snapshot_sentiment(self, turn: int):
        """保存情绪快照"""
        self.current_sentiment.heat_index = self.heat_index
        import copy
        self.sentiment_history.append(copy.deepcopy(self.current_sentiment))
        if len(self.sentiment_history) > 50:
            self.sentiment_history = self.sentiment_history[-50:]

    def decay(self):
        """每回合衰减"""
        self.heat_index = max(0, self.heat_index * 0.85)
        # 情绪缓慢回归中性
        self.current_sentiment.positive_ratio += (0.4 - self.current_sentiment.positive_ratio) * 0.05
        self.current_sentiment.negative_ratio += (0.2 - self.current_sentiment.negative_ratio) * 0.05
        self.current_sentiment.neutral_ratio = max(0.05, 1 - self.current_sentiment.positive_ratio - self.current_sentiment.negative_ratio)

    def get_state(self) -> dict:
        return {
            "heat_index": self.heat_index,
            "sentiment": {
                "polarity": self.current_sentiment.overall_polarity.value,
                "positive": f"{self.current_sentiment.positive_ratio:.1%}",
                "negative": f"{self.current_sentiment.negative_ratio:.1%}",
                "neutral": f"{self.current_sentiment.neutral_ratio:.1%}",
            },
            "approval_scores": {
                name: f"{score:.0f}" for name, score in
                {self.agent_names[aid]: s for aid, s in self.agent_approval.items()}.items()
            },
        }

    def get_description(self) -> str:
        lines = ["【公众舆论】"]
        s = self.current_sentiment
        lines.append(f"  热度指数: {self.heat_index:.0f}/100")
        lines.append(f"  情绪分布: 正面{s.positive_ratio:.0%} | 中性{s.neutral_ratio:.0%} | 负面{s.negative_ratio:.0%}")
        if s.poll_scores:
            scores_str = " | ".join(f"{n}:{v:.0f}" for n, v in s.poll_scores.items())
            lines.append(f"  好感度: {scores_str}")
        if self.pending_fan_reactions:
            fan = self.pending_fan_reactions[-1]
            lines.append(f"  粉丝动态: {fan.agent_name}的粉丝→{fan.reaction_type.value} (强度{fan.intensity:.0%})")
        self.pending_fan_reactions.clear()
        return "\n".join(lines)

    def reset(self):
        self.heat_index = 0
        self.current_sentiment = NetizenSentiment()
        self.sentiment_history.clear()
        self.pending_fan_reactions.clear()
        for aid in self.agent_approval:
            self.agent_approval[aid] = 60.0
