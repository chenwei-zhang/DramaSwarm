"""
数据模型 - 爬取数据的结构定义
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DataSourceType(Enum):
    """数据源类型"""
    BAIDU_BAIKE = "baidu_baike"
    ZHIHU = "zhihu"
    WEIBO = "weibo"
    DOUBAN = "douban"
    SOHU = "sohu"
    SINA = "sina"
    NETEASE = "netease"
    IFENG = "ifeng"
    TOUTIAO = "toutiao"


class GossipType(Enum):
    """八卦类型"""
    ROMANCE = "romance"  # 恋情
    SCANDAL = "scandal"  # 丑闻
    CONTROVERSY = "controversy"  # 争议
    RUMOR = "rumor"  # 谣言
    BREAKUP = "breakup"  # 分手
    MARRIAGE = "marriage"  # 婚姻
    DIVORCE = "divorce"  # 离婚
    CHEATING = "cheating"  # 出轨
    FEUD = "feud"  # 争端
    OTHER = "other"


@dataclass
class CelebrityProfile:
    """明星资料"""
    name: str
    english_name: str = ""
    birth_date: str | None = None
    birth_place: str = ""
    age: int = 0
    zodiac: str = ""
    constellation: str = ""  # 星座

    # 职业信息
    occupation: list[str] = field(default_factory=list)
    company: str = ""  # 经纪公司
    agency: str = ""  # 经纪人

    # 外貌特征
    height: str = ""
    weight: str = ""
    blood_type: str = ""

    # 基本信息详情
    biography: str = ""
    education: str = ""
    alma_mater: str = ""  # 母校

    # 作品列表
    works: list[str] = field(default_factory=list)
    famous_works: list[str] = field(default_factory=list)  # 代表作

    # 社交媒体
    weibo_id: str = ""
    weibo_followers: int = 0
    douyin_id: str = ""

    # 数据源
    sources: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)

    # 获取头像URL
    avatar_url: str = ""

    # 热度指标
    popularity_score: float = 0.0
    hot_search_count: int = 0


@dataclass
class GossipItem:
    """八卦条目"""
    title: str
    content: str
    gossip_type: GossipType = GossipType.OTHER
    date: str | None = None
    involved_celebrities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5  # 0-1，热度/重要性

    # 时间线
    start_date: str | None = None
    end_date: str | None = None
    is_ongoing: bool = False

    # 关联信息
    related_gossip: list[str] = field(default_factory=list)  # 相关八卦ID
    related_news: list[str] = field(default_factory=list)  # 相关新闻ID

    # 验证状态
    verified: bool = False  # 是否已被证实
    denial_exists: bool = False  # 是否有方否认

    # 来源
    source_url: str = ""
    source_type: DataSourceType = DataSourceType.BAIDU_BAIKE
    created_at: datetime = field(default_factory=datetime.now)

    # 热度数据
    views: int = 0
    shares: int = 0
    comments_count: int = 0

    # 情感倾向
    sentiment: str = "neutral"  # positive, negative, neutral
    sentiment_score: float = 0.0  # -1 to 1


@dataclass
class Relationship:
    """人物关系"""
    person_a: str
    person_b: str
    relation_type: str  # 夫妻、前任、恋人、绯闻、同事、朋友、对手等
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = True  # 是否为当前关系

    # 关系详情
    description: str = ""
    events: list[str] = field(default_factory=list)  # 关系中的重要事件
    milestones: list[dict] = field(default_factory=list)  # 重要里程碑

    # 可信度
    confidence: float = 0.8  # 0-1
    sources: list[str] = field(default_factory=list)

    # 关系强度
    strength: float = 0.5  # 0-1, 关系紧密程度

    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ScrapeResult:
    """爬取结果"""
    celebrity: CelebrityProfile
    gossips: list[GossipItem] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    # 社交媒体和新闻
    news_articles: list[NewsArticle] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    social_media_posts: list[SocialMediaPost] = field(default_factory=list)

    # 统计信息
    total_requests: int = 0
    success_rate: float = 1.0
    errors: list[str] = field(default_factory=list)

    # 数据质量
    data_completeness: float = 0.0  # 0-1, 数据完整度
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class NewsArticle:
    """新闻文章"""
    title: str
    content: str
    summary: str = ""
    publish_date: str | None = None
    author: str = ""
    source: str = ""  # 媒体名称
    source_url: str = ""
    source_type: DataSourceType = DataSourceType.SINA

    # 涉及的明星
    mentioned_celebrities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str = ""  # 娱乐、时尚、音乐等

    # 热度指标
    views: int = 0
    likes: int = 0
    comments_count: int = 0
    shares: int = 0

    # 情感分析
    sentiment: str = "neutral"  # positive, negative, neutral
    sentiment_score: float = 0.0  # -1 to 1

    # 相关八卦
    related_gossip_types: list[GossipType] = field(default_factory=list)

    # 图片
    images: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Comment:
    """评论"""
    id: str = ""
    content: str = ""
    author: str = ""  # 评论者昵称
    author_id: str = ""

    # 情感与影响
    likes: int = 0
    replies: int = 0
    is_top: bool = False  # 是否为热门评论
    is_author_verified: bool = False  # 评论者是否认证

    # 时间
    publish_time: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    # 来源
    source_url: str = ""
    source_platform: str = ""  # weibo, zhihu, douban, etc.

    # 回复
    parent_id: str = ""  # 父评论ID
    reply_to_id: str = ""  # 回复的评论ID
    reply_to_name: str = ""  # 回复的人

    # 涉及明星
    mentioned_celebrities: list[str] = field(default_factory=list)

    # 情感
    sentiment: str = "neutral"
    sentiment_score: float = 0.0

    # 子评论
    sub_comments: list[Comment] = field(default_factory=list)


@dataclass
class SocialMediaPost:
    """社交媒体动态"""
    id: str = ""
    platform: str = ""  # weibo, zhihu, douyin, douban
    author: str = ""
    author_id: str = ""
    author_verified: bool = False

    content: str = ""
    images: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)

    # 互动数据
    likes: int = 0
    reposts: int = 0
    comments: int = 0

    # 发布时间
    publish_time: str | None = None
    publish_timestamp: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    # 来源
    source_url: str = ""

    # 标签和话题
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)

    # 位置信息
    location: str = ""

    # 是否为广告/推广
    is_ad: bool = False

    # 关联的微博（如果是转发）
    repost_from_id: str = ""
    repost_from_author: str = ""


@dataclass
class HotSearchItem:
    """热搜条目"""
    title: str
    rank: int = 0
    heat: int = 0
    category: str = "娱乐"
    related_celebrities: list[str] = field(default_factory=list)
    url: str = ""
    platform: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Work:
    """影视作品"""
    title: str = ""
    year: int = 0
    type: str = ""  # 电影、电视剧、综艺等
    role: str = ""  # 饰演角色
    character_name: str = ""  # 角色名
    director: str = ""
    co_stars: list[str] = field(default_factory=list)
    rating: float = 0.0
    box_office: str = ""
    awards: list[str] = field(default_factory=list)
