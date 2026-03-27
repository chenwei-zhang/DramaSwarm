"""
数据模型 - 爬取数据的结构定义
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DataSourceType(Enum):
    """数据源类型"""
    BAIDU_BAIKE = "baidu_baike"
    ZHIDAO = "zhidao"
    WEIBO = "weibo"
    DOUBAN = "douban"
    SOHU = "sohu"
    SINA = "sina"
    NETEASE = "netease"


@dataclass
class CelebrityProfile:
    """明星资料"""
    name: str
    english_name: str = ""
    birth_date: str | None = None
    birth_place: str = ""
    occupation: list[str] = field(default_factory=list)
    company: str = ""  # 经纪公司

    # 外貌特征
    height: str = ""
    weight: str = ""
    zodiac: str = ""

    # 基本信息详情
    biography: str = ""
    education: str = ""

    # 作品列表
    works: list[str] = field(default_factory=list)

    # 数据源
    sources: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class GossipItem:
    """八卦条目"""
    title: str
    content: str
    date: str | None = None
    involved_celebrities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5  # 0-1，热度/重要性

    # 关联信息
    related_gossip: list[str] = field(default_factory=list)  # 相关八卦ID

    # 来源
    source_url: str = ""
    source_type: DataSourceType = DataSourceType.BAIDU_BAIKE
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Relationship:
    """人物关系"""
    person_a: str
    person_b: str
    relation_type: str  # 夫妻、前任、恋人、绯闻、同事、朋友、对手等
    start_date: str | None = None
    end_date: str | None = None

    # 关系详情
    description: str = ""
    events: list[str] = field(default_factory=list)  # 关系中的重要事件

    # 可信度
    confidence: float = 0.8  # 0-1

    # 来源
    sources: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ScrapeResult:
    """爬取结果"""
    celebrity: CelebrityProfile
    gossips: list[GossipItem] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    # 统计信息
    total_requests: int = 0
    success_rate: float = 1.0
    errors: list[str] = field(default_factory=list)
