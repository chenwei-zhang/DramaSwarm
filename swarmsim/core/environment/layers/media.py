# -*- coding: utf-8 -*-
"""
媒体层 - 娱乐媒体报道、标题生成
"""

from __future__ import annotations

import random

from ..models import (
    ReactionEvent, MediaCoverage,
    SentimentPolarity, MediaType
)
from .base import ReactionLayer


# 媒体机构
MEDIA_OUTLETS = [
    {"name": "娱乐头条", "type": MediaType.TABLOID, "amplify": 1.5, "style": "夸张"},
    {"name": "新浪娱乐", "type": MediaType.MAINSTREAM, "amplify": 1.0, "style": "中立"},
    {"name": "搜狐娱乐", "type": MediaType.MAINSTREAM, "amplify": 1.1, "style": "中立"},
    {"name": "财经观察", "type": MediaType.FINANCIAL, "amplify": 0.7, "style": "理性"},
    {"name": "八卦小报", "type": MediaType.TABLOID, "amplify": 1.8, "style": "煽情"},
    {"name": "自媒体大V", "type": MediaType.SELF_MEDIA, "amplify": 1.3, "style": "主观"},
]

# 标题模板
HEADLINE_TEMPLATES = {
    "negative": [
        "{names}{action}，网友炸了！",
        "震惊！{names}{action}，现场气氛降至冰点",
        "{names}陷争议风波，{action}引发热议",
        "最新爆料：{names}{action}，娱乐圈再起波澜",
    ],
    "positive": [
        "{names}{action}，获网友一致好评！",
        "{names}实力圈粉，{action}让人刮目相看",
        "正能量！{names}{action}获赞无数",
    ],
    "neutral": [
        "{names}{action}，引发各方关注",
        "最新消息：{names}就{action}作出回应",
    ],
}

# 动作词提取
ACTION_WORDS = {
    "怒怼": "怒怼对方", "批评": "公开批评", "道歉": "公开道歉",
    "宣布": "宣布重大消息", "爆料": "爆料内幕", "澄清": "澄清传闻",
    "分手": "官宣分手", "结婚": "官宣婚讯", "离婚": "官宣离婚",
    "出轨": "被曝出轨", "获奖": "斩获大奖", "代言": "签约代言",
}


class MediaLayer(ReactionLayer):
    """媒体反应层"""

    layer_name = "media"

    def __init__(self):
        self.agent_media_scores: dict[str, float] = {}
        self.current_headlines: list[MediaCoverage] = []
        self.coverage_history: list[MediaCoverage] = []

    def register_agent(self, agent_id: str, initial_score: float = 50.0):
        self.agent_media_scores[agent_id] = initial_score

    def react(self, event_description: str, severity: float,
              source: str, context: dict) -> list[ReactionEvent]:
        reactions = []
        self.current_headlines.clear()

        # 为每个媒体机构生成报道
        num_outlets = random.randint(1, min(3, len(MEDIA_OUTLETS)))
        selected = random.sample(MEDIA_OUTLETS, num_outlets)

        for outlet in selected:
            coverage = self._generate_coverage(outlet, event_description, severity, source)
            self.current_headlines.append(coverage)
            self.coverage_history.append(coverage)

            reactions.append(ReactionEvent(
                source_event_id=context.get("event_id", ""),
                reaction_layer=self.layer_name,
                severity=coverage.reach_score,
                target_agent_ids=[],
                description=f"[{coverage.media_name}] {coverage.headline}",
            ))

        # 更新涉事明星的媒体评分
        if severity > 0.5:
            for aid in self.agent_media_scores:
                if any(self.agent_media_scores.get(aid, 0) > 0 for _ in [1]):
                    pass  # 留给更精确的关联逻辑

        if len(self.coverage_history) > 100:
            self.coverage_history = self.coverage_history[-100:]

        return reactions

    def _generate_coverage(self, outlet: dict, event: str,
                           severity: float, source: str) -> MediaCoverage:
        """生成一条媒体报道"""
        amplified_severity = min(1.0, severity * outlet["amplify"])

        # 选择标题模板
        if amplified_severity > 0.6:
            sentiment = SentimentPolarity.NEGATIVE
            templates = HEADLINE_TEMPLATES["negative"]
        elif amplified_severity < 0.3:
            sentiment = SentimentPolarity.POSITIVE
            templates = HEADLINE_TEMPLATES["positive"]
        else:
            sentiment = SentimentPolarity.NEUTRAL
            templates = HEADLINE_TEMPLATES["neutral"]

        template = random.choice(templates)

        # 提取动作词
        action = "引发热议"
        for word, replacement in ACTION_WORDS.items():
            if word in event:
                action = replacement
                break

        headline = template.format(names=source, action=action)
        if outlet["style"] == "夸张":
            headline = headline.rstrip("！。") + "！！！"
        elif outlet["style"] == "煽情":
            headline = "独家：" + headline

        # 角度
        angles = {
            MediaType.TABLOID: random.choice(["冲突视角", "爆料视角", "阴谋论视角"]),
            MediaType.MAINSTREAM: random.choice(["中立报道", "多方核实", "深度分析"]),
            MediaType.FINANCIAL: random.choice(["商业影响", "股价波动", "品牌策略"]),
            MediaType.SELF_MEDIA: random.choice(["个人观点", "独家解读", "圈内消息"]),
        }

        return MediaCoverage(
            media_name=outlet["name"],
            media_type=outlet["type"],
            headline=headline,
            sentiment=sentiment,
            reach_score=amplified_severity * random.uniform(0.6, 1.0),
            angle=angles.get(outlet["type"], "中立报道"),
        )

    def decay(self):
        """头条过期"""
        # 保留最近10条
        self.current_headlines = self.current_headlines[-3:]

    def get_state(self) -> dict:
        return {
            "current_headlines": [
                {"media": c.media_name, "headline": c.headline, "reach": f"{c.reach_score:.0%}"}
                for c in self.current_headlines
            ],
        }

    def get_description(self) -> str:
        lines = ["【媒体报道】"]
        if self.current_headlines:
            for c in self.current_headlines[:3]:
                lines.append(f"  [{c.media_name}] {c.headline} (触达:{c.reach_score:.0%})")
        else:
            lines.append("  暂无相关报道")
        return "\n".join(lines)

    def reset(self):
        self.current_headlines.clear()
        self.coverage_history.clear()
        for aid in self.agent_media_scores:
            self.agent_media_scores[aid] = 50.0
