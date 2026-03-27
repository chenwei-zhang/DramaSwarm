# -*- coding: utf-8 -*-
"""
ReactionBus - 反应协调器

将事件按优先级分发到各反应层，收集结果并生成快照。
"""

from __future__ import annotations

from .models import ReactionEvent, EnvironmentReactionSnapshot
from .layers.base import ReactionLayer
from .layers import (
    PublicOpinionLayer,
    MediaLayer,
    SocialPlatformLayer,
    GovernmentLayer,
    CommercialLayer,
)


class ReactionBus:
    """
    反应总线：按优先级将事件分发到各反应层。

    优先级顺序（模拟因果关系）：
      1. public_opinion  → 先有舆论
      2. media           → 媒体跟进报道
      3. social_platform → 热搜发酵
      4. government      → 监管介入
      5. commercial      → 品牌反应
    """

    def __init__(self):
        # 按优先级注册的层列表
        self._layers: list[ReactionLayer] = []
        self._layer_map: dict[str, ReactionLayer] = {}

        # 创建默认五层
        self._init_default_layers()

        # 历史快照
        self.snapshots: list[EnvironmentReactionSnapshot] = []

    def _init_default_layers(self):
        """初始化默认五大反应层"""
        layers = [
            PublicOpinionLayer(),
            MediaLayer(),
            SocialPlatformLayer(),
            GovernmentLayer(),
            CommercialLayer(),
        ]
        for layer in layers:
            self._layers.append(layer)
            self._layer_map[layer.layer_name] = layer

    # ── Agent 注册 ──

    def register_agent(self, agent_id: str, agent_name: str):
        """将一个明星注册到所有反应层"""
        self._layer_map["public_opinion"].register_agent(agent_id, agent_name)
        self._layer_map["media"].register_agent(agent_id)
        self._layer_map["social_platform"].register_agent(agent_id)
        self._layer_map["government"].register_agent(agent_id)
        self._layer_map["commercial"].register_agent(agent_id, agent_name)

    # ── 核心分发 ──

    def dispatch(
        self,
        event_description: str,
        severity: float,
        source: str,
        context: dict,
    ) -> list[ReactionEvent]:
        """
        将事件分发到所有层，收集全部反应。

        Args:
            event_description: 事件描述文本
            severity: 严重度 0-1
            source: 来源 agent 名字或 "system"
            context: 共享上下文（会被逐层丰富）

        Returns:
            所有层产生的 ReactionEvent 列表
        """
        all_reactions: list[ReactionEvent] = []

        # 用一份可变 context，让前面的层写入后面的层可读
        ctx = dict(context)

        for layer in self._layers:
            # 把公众好感度注入 context，供后续层使用
            if layer.layer_name == "public_opinion":
                pass  # 第一层，无需额外注入
            elif "public_opinion" in self._layer_map:
                approval = self._layer_map["public_opinion"].agent_approval
                approval_scores = {
                    self._layer_map["public_opinion"].agent_names.get(aid, ""): score
                    for aid, score in approval.items()
                }
                ctx["approval_scores"] = approval_scores

            reactions = layer.react(event_description, severity, source, ctx)
            all_reactions.extend(reactions)

            # 政府监管影响社交平台（审查降热度）
            if layer.layer_name == "government":
                gov = self._layer_map["government"]
                for kw in gov.state.triggered_keywords[-3:]:
                    self._layer_map["social_platform"].censor_topic(kw)

        return all_reactions

    # ── 快照 ──

    def take_snapshot(self, turn_number: int) -> EnvironmentReactionSnapshot:
        """拍摄当前所有层的状态快照"""
        import copy

        po = self._layer_map["public_opinion"]
        media = self._layer_map["media"]
        social = self._layer_map["social_platform"]
        gov = self._layer_map["government"]
        comm = self._layer_map["commercial"]

        snapshot = EnvironmentReactionSnapshot(
            turn_number=turn_number,
            netizen_sentiment=copy.deepcopy(po.current_sentiment),
            fan_reactions=list(po.pending_fan_reactions),
            media_coverages=list(media.current_headlines),
            regulatory_state=copy.deepcopy(gov.state),
            brand_statuses=list(comm.brand_statuses.values()),
            trending_topics=list(social.hot_search_board),
            global_tension=po.heat_index / 100,
            global_mood=po.current_sentiment.positive_ratio,
        )

        self.snapshots.append(snapshot)
        if len(self.snapshots) > 200:
            self.snapshots = self.snapshots[-200:]

        return snapshot

    # ── 衰减 ──

    def decay(self):
        """每回合调用，让各层数据自然衰减"""
        for layer in self._layers:
            layer.decay()

    # ── 描述 ──

    def get_description(self) -> str:
        """所有层的中文描述（供 agent perceive 使用）"""
        parts = []
        for layer in self._layers:
            desc = layer.get_description()
            if desc.strip():
                parts.append(desc)
        return "\n".join(parts)

    def get_perception_for_agent(self, agent_id: str) -> str:
        """为特定 agent 生成个性化的反应感知文本"""
        parts = []

        # 公众舆论
        po = self._layer_map["public_opinion"]
        name = po.agent_names.get(agent_id, "")
        if name:
            approval = po.agent_approval.get(agent_id, 60)
            parts.append(f"你的当前好感度: {approval:.0f}/100")

            # 该 agent 的粉丝反应
            for fan in po.pending_fan_reactions:
                if fan.agent_name == name and fan.sample_comments:
                    parts.append(f"粉丝动态: {fan.sample_comments[0]}")
                    break

        # 热搜
        social = self._layer_map["social_platform"]
        related = [t for t in social.hot_search_board if name in t.title or name in " ".join(t.related_agents)]
        if related:
            top = related[0]
            parts.append(f"你相关热搜: 第{top.rank}名 {top.title} (热度{top.heat // 1000}k)")

        # 媒体
        media = self._layer_map["media"]
        for c in media.current_headlines[:2]:
            if name in c.headline:
                parts.append(f"媒体报道: [{c.media_name}] {c.headline}")
                break

        # 监管
        gov = self._layer_map["government"]
        if agent_id in gov.agent_actions and gov.agent_actions[agent_id].value != "none":
            parts.append(f"监管状态: {gov.agent_actions[agent_id].value}")
            if gov.state.warning_text:
                parts.append(f"  {gov.state.warning_text}")

        # 商业
        comm = self._layer_map["commercial"]
        status = comm.brand_statuses.get(agent_id)
        if status:
            non_continue = {b: a for b, a in status.brand_actions.items()
                           if a.value != "continue"}
            if non_continue:
                brands_str = "、".join(f"{b}({comm._action_label(a)})" for b, a in non_continue.items())
                parts.append(f"品牌动态: {brands_str}")
            parts.append(f"商业价值: {status.commercial_value:.0f}")

        return "\n".join(parts) if parts else ""

    # ── 状态导出 ──

    def get_state(self) -> dict:
        """所有层的状态汇总"""
        return {name: layer.get_state() for name, layer in self._layer_map.items()}

    def reset(self):
        """重置所有层"""
        for layer in self._layers:
            layer.reset()
        self.snapshots.clear()
