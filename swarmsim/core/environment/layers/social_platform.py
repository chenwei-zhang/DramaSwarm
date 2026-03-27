# -*- coding: utf-8 -*-
"""
社交平台层 - 热搜榜、评论区、曝光量
"""

from __future__ import annotations

import random

from ..models import (
    ReactionEvent, TrendingTopic,
    TrendingRankChange
)
from .base import ReactionLayer


class SocialPlatformLayer(ReactionLayer):
    """社交平台反应层"""

    layer_name = "social_platform"

    def __init__(self, max_trending: int = 50):
        self.hot_search_board: list[TrendingTopic] = []
        self.max_trending = max_trending
        self.agent_reach: dict[str, float] = {}      # agent_id -> 0-1 曝光度
        self.censored_topics: set[str] = set()

    def register_agent(self, agent_id: str, initial_reach: float = 0.5):
        self.agent_reach[agent_id] = initial_reach

    def react(self, event_description: str, severity: float,
              source: str, context: dict) -> list[ReactionEvent]:
        reactions = []

        # 高严重度事件上热搜
        if severity >= 0.3:
            topic = self._generate_trending(event_description, severity, source, context)
            if topic:
                self._add_to_board(topic)
                reactions.append(ReactionEvent(
                    source_event_id=context.get("event_id", ""),
                    reaction_layer=self.layer_name,
                    severity=topic.visibility,
                    target_agent_ids=[],
                    description=f"热搜第{topic.rank}：{topic.title}（热度{topic.heat}）",
                ))

                # 更新涉及明星曝光度
                for name in topic.related_agents:
                    for aid, reach in self.agent_reach.items():
                        self.agent_reach[aid] = min(1.0, reach + severity * 0.1)

        return reactions

    def _generate_trending(self, event: str, severity: float,
                           source: str, context: dict) -> TrendingTopic | None:
        """生成一个热搜话题"""
        # 生成话题标题
        if len(event) > 20:
            title = f"#{event[:18]}...#"
        else:
            title = f"#{event}#"

        # 如果已有相似话题，提升热度
        for existing in self.hot_search_board:
            if source in existing.title or any(kw in existing.title for kw in event[:4:]):
                existing.heat += int(severity * 50000)
                existing.rank_change = TrendingRankChange.RISING
                return None

        heat = int(severity * random.randint(50000, 200000))
        rank = self._estimate_rank(heat)

        # 评论区主题
        comment_themes = []
        if severity > 0.5:
            comment_themes = random.sample([
                "这也太过分了", "心疼当事人", "节目效果吧",
                "又是剧本", "等一个反转", "吃瓜群众路过",
            ], 3)
        else:
            comment_themes = random.sample([
                "平平无奇", "无聊", "看看就好",
                "关注后续", "就这样吧",
            ], 2)

        return TrendingTopic(
            title=title,
            rank=rank,
            heat=heat,
            rank_change=TrendingRankChange.NEW_ENTRY,
            related_agents=[source],
            platform=random.choice(["weibo", "douyin", "weibo"]),
            comment_summary="、".join(comment_themes),
            visibility=min(1.0, severity * 1.2),
        )

    def _estimate_rank(self, heat: int) -> int:
        """根据热度估算排名"""
        rank = 1
        for topic in self.hot_search_board:
            if heat > topic.heat:
                break
            rank += 1
        return min(rank, self.max_trending)

    def _add_to_board(self, topic: TrendingTopic):
        """添加到热搜榜"""
        self.hot_search_board.append(topic)
        # 按热度排序
        self.hot_search_board.sort(key=lambda t: t.heat, reverse=True)
        # 更新排名
        for i, t in enumerate(self.hot_search_board):
            t.rank = i + 1
        # 裁剪
        if len(self.hot_search_board) > self.max_trending:
            self.hot_search_board = self.hot_search_board[:self.max_trending]

    def censor_topic(self, keyword: str):
        """审查某个话题（被 GovernmentLayer 调用）"""
        self.censored_topics.add(keyword)
        for topic in self.hot_search_board:
            if keyword in topic.title:
                topic.rank_change = TrendingRankChange.FALLING
                topic.heat = int(topic.heat * 0.3)
                topic.visibility *= 0.3

    def decay(self):
        """热搜衰减"""
        for topic in self.hot_search_board:
            topic.heat = int(topic.heat * 0.8)
            if topic.rank_change != TrendingRankChange.NEW_ENTRY:
                topic.rank_change = TrendingRankChange.FALLING

        # 移除热度太低的话题
        self.hot_search_board = [t for t in self.hot_search_board if t.heat > 1000]
        # 重新排名
        for i, t in enumerate(self.hot_search_board):
            t.rank = i + 1

    def get_state(self) -> dict:
        return {
            "hot_search": [
                {"rank": t.rank, "title": t.title, "heat": t.heat, "change": t.rank_change.value}
                for t in self.hot_search_board[:10]
            ],
            "censored_count": len(self.censored_topics),
        }

    def get_description(self) -> str:
        lines = ["【热搜榜】"]
        if self.hot_search_board:
            for t in self.hot_search_board[:5]:
                change_icon = {"rising": "↑", "falling": "↓", "new_entry": "★"}.get(t.rank_change.value, "→")
                lines.append(f"  {t.rank}. {change_icon} {t.title} (热度{t.heat // 1000}k)")
        else:
            lines.append("  暂无热搜")
        if self.censored_topics:
            lines.append(f"  已审查话题: {len(self.censored_topics)}个")
        return "\n".join(lines)

    def reset(self):
        self.hot_search_board.clear()
        self.censored_topics.clear()
        for aid in self.agent_reach:
            self.agent_reach[aid] = 0.5
