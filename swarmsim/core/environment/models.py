# -*- coding: utf-8 -*-
"""
环境反应系统 - 数据模型定义
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ── 枚举 ──

class SentimentPolarity(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class FanReactionType(Enum):
    SUPPORTIVE = "supportive"         # 力挺偶像
    DEFENSIVE = "defensive"          # 护犊反击
    ANGRY = "angry"                  # 愤怒出征
    DISAPPOINTED = "disappointed"    # 脱粉回踩
    INDIGNANT = "indignant"          # 路人愤怒
    MELON_EATING = "melon_eating"    # 路人吃瓜


class MediaType(Enum):
    TABLOID = "tabloid"                       # 八卦媒体（放大戏剧性）
    MAINSTREAM = "mainstream"                 # 主流媒体（克制）
    FINANCIAL = "financial"                   # 财经媒体（关注商业）
    SOCIAL_OFFICIAL = "social_official"       # 社交平台官方号
    SELF_MEDIA = "self_media"                 # 自媒体大V


class RegulatoryAction(Enum):
    NONE = "none"
    KEYWORD_WARNING = "keyword_warning"               # 关键词屏蔽
    CONTENT_REMOVAL = "content_removal"               # 内容下架
    ACCOUNT_RESTRICTION = "account_restriction"        # 账号限流
    OFFICIAL_WARNING = "official_warning"              # 官方约谈警告
    TEMPORARY_BAN = "temporary_ban"                    # 临时禁言
    PERMANENT_BAN = "permanent_ban"                    # 永久封禁/劣迹艺人


class BrandAction(Enum):
    CONTINUE = "continue"             # 继续合作
    MONITORING = "monitoring"         # 观望中
    NEGOTIATING = "negotiating"       # 重新谈判
    SUSPENDED = "suspended"           # 暂停合作
    TERMINATED = "terminated"         # 解约
    LAWSUIT = "lawsuit"               # 索赔起诉


class TrendingRankChange(Enum):
    NEW_ENTRY = "new_entry"
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    REMOVED = "removed"


# ── 数据类 ──

@dataclass
class ReactionEvent:
    """反应事件 - 在各层之间传播"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_event_id: str = ""
    reaction_layer: str = ""           # public_opinion / media / social / government / commercial
    severity: float = 0.5
    target_agent_ids: list[str] = field(default_factory=list)
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class NetizenSentiment:
    """网民情绪快照"""
    overall_polarity: SentimentPolarity = SentimentPolarity.NEUTRAL
    positive_ratio: float = 0.4
    negative_ratio: float = 0.2
    neutral_ratio: float = 0.4
    heat_index: float = 0.0            # 0-100
    keywords: list[str] = field(default_factory=list)
    poll_scores: dict[str, float] = field(default_factory=dict)  # agent_name -> 好感度 0-100


@dataclass
class FanReaction:
    """粉丝群体反应"""
    agent_name: str = ""
    reaction_type: FanReactionType = FanReactionType.SUPPORTIVE
    intensity: float = 0.5             # 0-1
    sample_comments: list[str] = field(default_factory=list)
    is_anti_fan: bool = False


@dataclass
class MediaCoverage:
    """媒体报道"""
    media_name: str = ""
    media_type: MediaType = MediaType.TABLOID
    headline: str = ""
    sentiment: SentimentPolarity = SentimentPolarity.NEUTRAL
    reach_score: float = 0.5           # 0-1
    angle: str = ""                    # 报道角度


@dataclass
class RegulatoryState:
    """政府/监管状态"""
    triggered_keywords: list[str] = field(default_factory=list)
    action: RegulatoryAction = RegulatoryAction.NONE
    warning_text: str = ""
    affected_agent_ids: list[str] = field(default_factory=list)
    escalation_level: int = 0          # 0-5 累计严重度


@dataclass
class BrandStatus:
    """品牌代言状态"""
    agent_id: str = ""
    agent_name: str = ""
    active_brands: list[str] = field(default_factory=list)
    commercial_value: float = 50.0     # 0-100
    brand_actions: dict[str, BrandAction] = field(default_factory=dict)  # brand -> action
    revenue_impact: float = 0.0


@dataclass
class TrendingTopic:
    """热搜条目"""
    title: str = ""
    rank: int = 0
    heat: int = 0
    rank_change: TrendingRankChange = TrendingRankChange.NEW_ENTRY
    related_agents: list[str] = field(default_factory=list)
    platform: str = "weibo"
    comment_summary: str = ""
    visibility: float = 0.5


@dataclass
class EnvironmentReactionSnapshot:
    """某一时刻所有层的状态快照"""
    turn_number: int = 0
    netizen_sentiment: NetizenSentiment = field(default_factory=NetizenSentiment)
    fan_reactions: list[FanReaction] = field(default_factory=list)
    media_coverages: list[MediaCoverage] = field(default_factory=list)
    regulatory_state: RegulatoryState = field(default_factory=RegulatoryState)
    brand_statuses: list[BrandStatus] = field(default_factory=list)
    trending_topics: list[TrendingTopic] = field(default_factory=list)
    global_tension: float = 0.3
    global_mood: float = 0.5
