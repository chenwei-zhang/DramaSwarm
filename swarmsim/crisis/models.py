# -*- coding: utf-8 -*-
"""
危机仿真数据模型

定义危机场景、动作、状态、干预条件、结果报告等核心数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── 枚举 ──

class CrisisPhase(Enum):
    """危机生命周期阶段"""
    BREAKOUT = "breakout"        # Day 1: 爆发期
    ESCALATION = "escalation"    # Day 2-3: 发酵期
    PEAK = "peak"                # Day 4-7: 高峰期
    MITIGATION = "mitigation"   # Day 8-14: 应对期
    RESOLUTION = "resolution"   # Day 15-21: 收尾期
    AFTERMATH = "aftermath"     # Day 22+: 余波期

    @property
    def label(self) -> str:
        return {
            "breakout": "爆发期", "escalation": "发酵期",
            "peak": "高峰期", "mitigation": "应对期",
            "resolution": "收尾期", "aftermath": "余波期",
        }.get(self.value, self.value)


class PRAction(Enum):
    """公关动作空间"""
    SILENCE = "silence"                # 沉默不回应
    APOLOGIZE = "apologize"            # 公开道歉
    STATEMENT = "statement"            # 发声明
    GO_ON_SHOW = "go_on_show"         # 上节目回应
    LAWSUIT = "lawsuit"                # 起诉造谣者
    PLAY_VICTIM = "play_victim"       # 卖惨/博同情
    COUNTERATTACK = "counterattack"   # 反击/否认
    HIDE = "hide"                     # 暂避风头
    CHARITY = "charity"               # 公益洗白
    COMEBACK = "comeback"             # 复出试水

    @property
    def label(self) -> str:
        return {
            "silence": "沉默不回应", "apologize": "公开道歉",
            "statement": "发声明", "go_on_show": "上节目回应",
            "lawsuit": "起诉造谣者", "play_victim": "卖惨博同情",
            "counterattack": "反击否认", "hide": "暂避风头",
            "charity": "公益洗白", "comeback": "复出试水",
        }.get(self.value, self.value)


class GossipType(Enum):
    """八卦类型"""
    CHEATING = "cheating"
    SCANDAL = "scandal"
    DIVORCE = "divorce"
    DRUGS = "drugs"
    TAX_EVASION = "tax_evasion"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            "cheating": "出轨", "scandal": "丑闻",
            "divorce": "离婚", "drugs": "吸毒",
            "tax_evasion": "偷税漏税", "other": "其他",
        }.get(self.value, self.value)


class CrisisRole(Enum):
    """危机中的角色"""
    PERPETRATOR = "perpetrator"  # 加害者（出轨方/涉毒者/逃税者）
    VICTIM = "victim"            # 受害者（被出轨方/受害者）
    ACCOMPLICE = "accomplice"    # 第三者/同谋
    BYSTANDER = "bystander"      # 旁观者（默认）

    @property
    def label(self) -> str:
        return {
            "perpetrator": "加害者",
            "victim": "受害者",
            "accomplice": "第三者",
            "bystander": "旁观者",
        }.get(self.value, self.value)


class InteractionMode(Enum):
    """交互模式"""
    CRISIS = "crisis"     # 6阶段危机仿真 + 10种PR动作
    FREE = "free"         # 自由互动模式

    @property
    def label(self) -> str:
        return {"crisis": "危机模式", "free": "自由互动"}.get(self.value, self.value)


class TriggerType(Enum):
    """干预触发类型"""
    TIME_ABSOLUTE = "time_absolute"    # 第 X 天触发
    TIME_RELATIVE = "time_relative"    # 仿真开始后 N 天触发
    STATE_THRESHOLD = "state_threshold"  # 状态阈值触发

    @property
    def label(self) -> str:
        return {
            "time_absolute": "指定日期",
            "time_relative": "相对天数",
            "state_threshold": "状态触发",
        }.get(self.value, self.value)


class FreeAction(Enum):
    """自由互动动作空间"""
    SPEAK = "speak"                # 公开发言/表态
    SUPPORT = "support"            # 支持/声援某人
    CRITICIZE = "criticize"          # 批评/抨击某人
    COLLABORATE = "collaborate"      # 合作/联名
    SOCIALIZE = "socialize"        # 社交/聚餐
    ANNOUNCE = "announce"          # 宣布/公布消息
    IGNORE = "ignore"              # 无视/冷处理
    PRIVATE_MSG = "private_msg"    # 私信/私下沟通

    MEDIATE = "mediate"            # 调停/撮合

    RUMOR = "rumor"              # 传谣/散布消息

    RETREAT = "retreat"            # 收缩/低调回避
    @property
    def label(self) -> str:
        return {
            "speak": "公开发言", "support": "支持声援",
            "criticize": "公开批评", "collaborate": "合作联名",
            "socialize": "社交聚餐", "announce": "宣布消息",
            "ignore": "无视冷处理", "private_msg": "私信沟通",
            "mediate": "调停撮合", "rumor": "传谣散布",
            "retreat": "低调回避",
        }.get(self.value, self.value)


class ExternalEventType(Enum):
    """外部事件类型"""
    MEDIA_REPORT = "media_report"          # 媒体特别报道
    VIDEO_LEAK = "video_leak"              # 视频/录音泄露
    COMPETITOR_ANNOUNCE = "competitor_announce"  # 竞争对手宣布
    REGULATORY_ACTION = "regulatory_action"      # 监管行动
    BRAND_DECISION = "brand_decision"            # 品牌决策
    CUSTOM = "custom"                            # 自定义事件

    @property
    def label(self) -> str:
        return {
            "media_report": "媒体特别报道",
            "video_leak": "视频/录音泄露",
            "competitor_announce": "竞争对手宣布",
            "regulatory_action": "监管行动",
            "brand_decision": "品牌决策",
            "custom": "自定义事件",
        }.get(self.value, self.value)


# ── 数据类 ──

@dataclass
class CrisisScenario:
    """危机场景定义"""
    scenario_id: str
    title: str
    crisis_date: str                      # 历史日期 YYYY-MM-DD
    description: str
    involved_persons: list[str]
    initial_severity: float               # 0-1
    gossip_type: GossipType
    historical_outcome: dict[str, Any]    # 真实结果（用于对比）
    pre_crisis_relationships: list[dict]  # [{person_a, person_b, type, strength}]
    is_custom: bool = False               # 是否为用户自定义场景
    interaction_mode: InteractionMode = InteractionMode.CRISIS
    person_roles: dict[str, CrisisRole] = field(default_factory=dict)  # 危机角色映射


@dataclass
class CrisisAction:
    """危机中的公关动作"""
    actor: str
    action: PRAction
    target: str | None = None
    content: str = ""
    day: int = 0
    effects: dict[str, float] = field(default_factory=dict)
    triggered_by: str | None = None        # 被谁的哪条动作触发
    trigger_relation: str | None = None    # 触发关系类型
    free_action: FreeAction | None = None   # 自由模式动作（自由模式时使用）


@dataclass
class AgentMessage:
    """Agent 间通信消息"""
    sender: str                            # "李小璐" 或 "audience_粉丝"
    receiver: str | None = None            # None = 广播
    action: PRAction | None = None
    content: str = ""
    day: int = 0
    sentiment: str = "neutral"             # positive/negative/neutral
    source: str = "celebrity"              # celebrity/audience


@dataclass
class TrendingTopic:
    """热搜话题"""
    rank: int
    title: str
    heat: float
    category: str = ""


@dataclass
class MediaHeadline:
    """媒体头条"""
    outlet: str
    headline: str
    sentiment: str = "neutral"
    reach: float = 0.5


@dataclass
class BrandStatus:
    """品牌代言状态"""
    brand: str
    action: str = "continue"   # continue/monitoring/suspended/terminated
    value: float = 60.0


@dataclass
class CrisisState:
    """危机仿真状态快照"""
    day: int
    phase: CrisisPhase
    approval_scores: dict[str, float] = field(default_factory=dict)
    brand_values: dict[str, float] = field(default_factory=dict)
    heat_index: float = 50.0
    trending_topics: list[TrendingTopic] = field(default_factory=list)
    media_headlines: list[MediaHeadline] = field(default_factory=list)
    rumor_count: int = 0
    rumors: list[dict] = field(default_factory=list)
    public_sentiment: dict[str, float] = field(default_factory=lambda: {
        "positive": 0.2, "negative": 0.5, "neutral": 0.3
    })
    regulatory_level: int = 0               # 0-5
    agent_actions: list[CrisisAction] = field(default_factory=list)
    active_interventions: list[dict] = field(default_factory=list)
    person_brands: dict[str, list[BrandStatus]] = field(default_factory=dict)
    audience_reactions: list[dict] = field(default_factory=list)
    interaction_log: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "phase": self.phase.value,
            "phase_label": self.phase.label,
            "approval_scores": self.approval_scores,
            "brand_values": self.brand_values,
            "heat_index": self.heat_index,
            "trending_topics": [
                {"rank": t.rank, "title": t.title, "heat": t.heat, "category": t.category}
                for t in self.trending_topics
            ],
            "media_headlines": [
                {"outlet": h.outlet, "headline": h.headline,
                 "sentiment": h.sentiment, "reach": h.reach}
                for h in self.media_headlines
            ],
            "rumor_count": self.rumor_count,
            "rumors": self.rumors,
            "public_sentiment": self.public_sentiment,
            "regulatory_level": self.regulatory_level,
            "agent_actions": [
                {"actor": a.actor, "action": a.action.value,
                 "action_label": a.action.label,
                 "free_action": a.free_action.value if a.free_action else None,
                 "free_action_label": a.free_action.label if a.free_action else None,
                 "content": a.content, "day": a.day,
                 "triggered_by": a.triggered_by,
                 "trigger_relation": a.trigger_relation}
                for a in self.agent_actions
            ],
            "active_interventions": self.active_interventions,
            "person_brands": {
                p: [{"brand": b.brand, "action": b.action, "value": b.value}
                    for b in brands]
                for p, brands in self.person_brands.items()
            },
            "audience_reactions": self.audience_reactions,
            "interaction_log": self.interaction_log,
        }


@dataclass
class InterventionCondition:
    """用户干预条件"""
    # 触发类型
    trigger_type: str = "time_absolute"    # time_absolute / time_relative / state_threshold
    day: int | None = None                 # 绝对日期 (time_absolute) 或相对天数 (time_relative)
    # 状态阈值触发
    metric: str | None = None              # 监控指标: approval / heat / brand / regulatory
    threshold: float | None = None         # 阈值
    comparator: str | None = None          # "lt"(<) / "gt"(>) / "lte"(<=) / "gte"(>=)
    # 动作
    person: str | None = None              # 目标人物
    action: str | None = None              # 强制 PR 动作
    external_event: str | None = None      # 注入外部事件描述
    event_type: str | None = None          # ExternalEventType 值
    # 关系变更
    person_a: str | None = None
    person_b: str | None = None
    relationship_change: str | None = None  # "strengthen" / "weaken" / "break" / "new"
    description: str = ""


@dataclass
class CrisisOutcomeReport:
    """危机仿真结果报告"""
    verdict: str                           # "better" / "worse" / "similar"
    verdict_label: str                     # 中文标签
    summary: str
    metrics_comparison: dict[str, dict] = field(default_factory=dict)
    pr_recommendations: list[str] = field(default_factory=list)
    key_differences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "verdict_label": self.verdict_label,
            "summary": self.summary,
            "metrics_comparison": self.metrics_comparison,
            "pr_recommendations": self.pr_recommendations,
            "key_differences": self.key_differences,
        }
