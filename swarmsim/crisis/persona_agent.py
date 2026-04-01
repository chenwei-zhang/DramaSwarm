# -*- coding: utf-8 -*-
"""
明星 Agent - 从 GraphRAG 构建人设

支持纯规则模式（无需 API key）和 LLM 模式。
规则模式基于 Big Five 性格特质和状态矩阵决策。
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Any

from swarmsim.crisis.models import (
    CrisisPhase, PRAction, CrisisAction, AgentMessage, FreeAction, CrisisRole, GossipType,
)
from swarmsim.graph.temporal import TemporalKnowledgeGraph
from swarmsim.memory.base import MemoryEntry, MemoryStore, InMemoryStore


# ── PR 动作对应的中文描述模板 ──

ACTION_DESCRIPTIONS: dict[PRAction, str] = {
    PRAction.SILENCE: "{name}选择沉默，不做任何回应",
    PRAction.APOLOGIZE: "{name}公开道歉，承认错误并请求原谅",
    PRAction.STATEMENT: "{name}发布官方声明澄清事实",
    PRAction.GO_ON_SHOW: "{name}上节目正面回应争议",
    PRAction.LAWSUIT: "{name}起诉造谣者，法律维权",
    PRAction.PLAY_VICTIM: "{name}展示脆弱面，表示自己才是受害者",
    PRAction.COUNTERATTACK: "{name}强力反击，否认所有指控",
    PRAction.HIDE: "{name}暂时隐退，避开公众视线",
    PRAction.CHARITY: "{name}参与公益活动，改善公众形象",
    PRAction.COMEBACK: "{name}尝试复出，发布新作品",
}

FREE_ACTION_DESCRIPTIONS: dict[FreeAction, str] = {
    FreeAction.SPEAK: "{name}公开发表了自己的看法",
    FreeAction.SUPPORT: "{name}公开支持了对方",
    FreeAction.CRITICIZE: "{name}公开批评了对方",
    FreeAction.COLLABORATE: "{name}宣布了一项合作计划",
    FreeAction.SOCIALIZE: "{name}参加了一场社交活动",
    FreeAction.ANNOUNCE: "{name}发布了一条重要声明",
    FreeAction.IGNORE: "{name}选择无视这一事件",
    FreeAction.PRIVATE_MSG: "{name}私下联系了对方",
    FreeAction.MEDIATE: "{name}出面调停了争端",
    FreeAction.RUMOR: "{name}传播了一条消息",
    FreeAction.RETREAT: "{name}选择了低调回避",
}


class CelebrityPersonaAgent:
    """从 GraphRAG 构建人设的明星 Agent"""

    def __init__(
        self,
        name: str,
        kg: TemporalKnowledgeGraph,
        use_llm: bool = False,
        memory_store: MemoryStore | None = None,
    ):
        self.name = name
        self.kg = kg
        self.use_llm = use_llm

        # 危机角色（由仿真引擎注入）
        self.crisis_role: CrisisRole = CrisisRole.BYSTANDER
        self.gossip_type: GossipType | None = None

        # 从图谱构建性格画像 (Big Five)
        self.personality = self._build_personality()

        # 结构化记忆系统
        self._memory_store = memory_store or InMemoryStore()
        self.memory: list[str] = []  # 保留兼容性（存储传播标记等简易信息）
        self.past_actions: list[PRAction] = []
        self._memory_counter = 0

    def _build_personality(self) -> dict[str, float]:
        """从图谱推断完整性格画像（Big Five + 扩展维度）

        使用确定性哈希代替 random.uniform()，保证同一明星人格一致。
        数据源：职业、bio、粉丝量、作品数、公司、历史事件、关系网络。
        """
        self._hash_counter = 0
        node_id = f"celebrity:{self.name}"

        if not self.kg._graph.has_node(node_id):
            return self._default_personality()

        data = dict(self.kg._graph.nodes[node_id])
        bio = str(data.get("biography", ""))
        occupation = data.get("occupation", [])
        if isinstance(occupation, str):
            occupation = [occupation]
        occ_text = " ".join(occupation)

        # ── Big Five 基线 ──
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }

        # ── 1. 职业推断 ──
        if any(kw in occ_text for kw in ["歌手", "偶像", "主持人"]):
            traits["extraversion"] = self._srand(0.6, 0.85)
            traits["openness"] = self._srand(0.6, 0.8)
        if any(kw in occ_text for kw in ["演员", "影帝", "影后"]):
            traits["openness"] = self._srand(0.5, 0.75)
            traits["conscientiousness"] = self._srand(0.55, 0.8)
        if any(kw in occ_text for kw in ["导演", "制片"]):
            traits["conscientiousness"] = self._srand(0.6, 0.85)
        if any(kw in occ_text for kw in ["模特", "idol"]):
            traits["extraversion"] = max(traits["extraversion"], self._srand(0.6, 0.8))
            traits["openness"] = max(traits["openness"], self._srand(0.5, 0.7))

        # ── 2. Bio 关键词推断 ──
        if any(kw in bio for kw in ["争议", "负面", "封杀", "出轨"]):
            traits["neuroticism"] = self._srand(0.55, 0.8)
            traits["agreeableness"] = self._srand(0.3, 0.5)
        if any(kw in bio for kw in ["慈善", "公益", "温暖", "人缘好"]):
            traits["agreeableness"] = self._srand(0.65, 0.85)
        if any(kw in bio for kw in ["低调", "内敛", "沉默"]):
            traits["extraversion"] = self._srand(0.2, 0.4)
        if any(kw in bio for kw in ["火爆", "直率", "敢说", "刚"]):
            traits["neuroticism"] = max(traits["neuroticism"], self._srand(0.6, 0.8))
            traits["agreeableness"] = min(traits["agreeableness"], self._srand(0.25, 0.45))
        if any(kw in bio for kw in ["才华", "实力", "演技", "唱功"]):
            traits["conscientiousness"] = max(traits["conscientiousness"], self._srand(0.6, 0.85))

        # ── 3. 粉丝量 → public_visibility + extraversion 修正 ──
        fans = data.get("weibo_followers", 0) or 0
        if fans >= 1e8:
            traits["public_visibility"] = 0.95
            traits["extraversion"] = min(1.0, traits["extraversion"] + 0.15)
        elif fans >= 5e7:
            traits["public_visibility"] = 0.75
        elif fans >= 1e7:
            traits["public_visibility"] = 0.6
        elif fans >= 1e6:
            traits["public_visibility"] = 0.4
        else:
            traits["public_visibility"] = 0.25

        # ── 4. 作品数量 → career_stage + conscientiousness ──
        works = data.get("famous_works", []) or []
        work_count = len(works)
        if work_count >= 8:
            traits["career_stage"] = 0.9
            traits["conscientiousness"] = min(1.0, traits["conscientiousness"] + 0.1)
        elif work_count >= 4:
            traits["career_stage"] = 0.6
        elif work_count >= 1:
            traits["career_stage"] = 0.35
        else:
            traits["career_stage"] = 0.15

        # ── 5. 公司类型 → media_savvy ──
        company = str(data.get("company", "") or "")
        if any(kw in company for kw in ["工作室", "个人"]):
            traits["media_savvy"] = self._srand(0.7, 0.9)
        elif any(kw in company for kw in ["娱乐", "传媒", "影视", "文化"]):
            traits["media_savvy"] = self._srand(0.5, 0.75)
        elif company:
            traits["media_savvy"] = self._srand(0.3, 0.5)
        else:
            traits["media_savvy"] = 0.4

        # ── 6. 历史事件分析 → controversy_history + neuroticism ──
        events = self.kg.get_person_timeline(self.name)
        gossip_events = [e for e in events if e.get("type") == "gossip"]
        total_importance = sum(e.get("importance", 0.3) for e in gossip_events)
        negative_events = [
            e for e in gossip_events
            if e.get("sentiment") == "negative"
        ]

        # 事件量 + 重要性 → 争议历史
        if total_importance > 2.0 or len(gossip_events) >= 4:
            traits["controversy_history"] = self._srand(0.7, 0.95)
        elif total_importance > 1.0 or len(gossip_events) >= 2:
            traits["controversy_history"] = self._srand(0.4, 0.7)
        else:
            traits["controversy_history"] = self._srand(0.1, 0.4)

        # 负面事件 → neuroticism 提升
        for event in gossip_events:
            gossip_type = event.get("gossip_type", "other")
            importance = event.get("importance", 0.3)
            if gossip_type in ("cheating", "scandal"):
                traits["neuroticism"] = max(traits["neuroticism"], 0.55 + importance * 0.3)
            elif gossip_type == "divorce":
                traits["neuroticism"] = max(traits["neuroticism"], 0.5 + importance * 0.2)
            elif gossip_type in ("drugs", "tax_evasion"):
                traits["neuroticism"] = max(traits["neuroticism"], 0.65 + importance * 0.2)
                traits["agreeableness"] = min(traits["agreeableness"], 0.4)

        # ── 7. 关系网络拓扑 → openness + agreeableness（含强度加权）──
        try:
            neighbors = self.kg.get_social_neighborhood(self.name, max_depth=1)
            conn_count = len(neighbors)
            # 连接类型统计
            rel_types = set()
            strong_rel_count = 0
            for n in neighbors:
                rels = self.kg.get_relationship_context(self.name, n)
                for r in rels:
                    rel_types.add(r.get("relation_type", ""))
                    if r.get("strength", 0.5) >= 0.7:
                        strong_rel_count += 1

            if conn_count >= 10:
                traits["openness"] = min(1.0, traits["openness"] + 0.15)
            elif conn_count >= 5:
                traits["openness"] = min(1.0, traits["openness"] + 0.08)

            # 强关系多 → 更容易信任他人
            if strong_rel_count >= 3:
                traits["agreeableness"] = min(1.0, traits["agreeableness"] + 0.1)

            if any(t in rel_types for t in ("配偶", "家人", "亲属", "闺蜜", "好友")):
                traits["agreeableness"] = min(1.0, traits["agreeableness"] + 0.08)
            if any(t in rel_types for t in ("对手", "宿敌", "竞争对手")):
                traits["neuroticism"] = min(1.0, traits["neuroticism"] + 0.05)

            # 二度连接数 → 社交广度 → openness
            try:
                neighbors_2 = self.kg.get_social_neighborhood(self.name, max_depth=2)
                indirect = len(set(neighbors_2) - set(neighbors))
                if indirect >= 15:
                    traits["openness"] = min(1.0, traits["openness"] + 0.1)
                elif indirect >= 8:
                    traits["openness"] = min(1.0, traits["openness"] + 0.05)
            except Exception:
                pass

        except Exception:
            pass

        # ── 7.5 年龄 → risk_tolerance + conscientiousness ──
        birth_date = data.get("birth_date", "")
        if birth_date:
            try:
                from datetime import datetime
                birth = datetime.strptime(str(birth_date)[:10], "%Y-%m-%d")
                age = (datetime.now() - birth).days // 365
                if age < 25:
                    traits["risk_tolerance"] = min(1.0, traits.get("risk_tolerance", 0.5) + 0.1)
                elif age > 45:
                    traits["conscientiousness"] = min(1.0, traits["conscientiousness"] + 0.1)
                    traits["risk_tolerance"] = max(0.0, traits.get("risk_tolerance", 0.5) - 0.05)
            except (ValueError, TypeError):
                pass

        # ── 7.6 正面新闻事件 → conscientiousness ──
        all_events = self.kg.get_person_timeline(self.name)
        positive_events = [
            e for e in all_events
            if e.get("type") == "news" and e.get("sentiment") == "positive"
        ]
        if len(positive_events) >= 3:
            traits["conscientiousness"] = min(1.0, traits["conscientiousness"] + 0.08)

        # ── 8. 从性格推导 risk_tolerance ──
        traits["risk_tolerance"] = (
            0.3 * traits["neuroticism"]
            + 0.3 * traits["extraversion"]
            + 0.2 * traits["openness"]
            + 0.2 * (1.0 - traits["agreeableness"])
        )

        # Clamp all to 0-1
        for key in traits:
            traits[key] = max(0.0, min(1.0, traits[key]))

        return traits

    def _srand(self, lo: float, hi: float) -> float:
        """确定性伪随机：基于 name + counter 的哈希"""
        seed_str = f"{self.name}_{self._hash_counter}"
        self._hash_counter += 1
        h = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        return lo + (h / 0xFFFFFFFF) * (hi - lo)

    @staticmethod
    def _default_personality() -> dict[str, float]:
        """默认人格（图谱中无数据时使用）"""
        return {
            "openness": 0.5, "conscientiousness": 0.5,
            "extraversion": 0.5, "agreeableness": 0.5,
            "neuroticism": 0.5,
            "risk_tolerance": 0.5, "public_visibility": 0.5,
            "career_stage": 0.5, "media_savvy": 0.5,
            "controversy_history": 0.3,
        }

    async def generate_crisis_response(
        self,
        phase: CrisisPhase,
        state: dict,
        forced_action: PRAction | None = None,
        peer_actions: list[CrisisAction] | None = None,
        audience_reactions: list[AgentMessage] | None = None,
    ) -> CrisisAction:
        """生成危机响应动作

        Args:
            phase: 当前危机阶段
            state: 当前仿真状态 {approval_scores, heat_index, ...}
            forced_action: 干预系统强制动作
            peer_actions: 今天已决策的其他 Agent 动作
            audience_reactions: 观众对今天已有动作的反应

        Returns:
            CrisisAction
        """
        peer_actions = peer_actions or []
        audience_reactions = audience_reactions or []

        if forced_action:
            action = forced_action
        elif self.use_llm:
            action = await self._llm_decide(phase, state, peer_actions, audience_reactions)
        else:
            action = self._rule_decide(phase, state, peer_actions, audience_reactions)

        content = ACTION_DESCRIPTIONS.get(action, "").format(name=self.name)

        # 检查是否被其他 Agent 触发
        triggered_by = None
        trigger_relation = None
        for peer in peer_actions:
            rels = self.kg.get_relationship_context(self.name, peer.actor)
            if rels:
                rel = rels[0]
                if rel.get("relation_type") in (
                    "配偶", "前配偶", "伴侣", "家人", "亲属",
                    "绯闻", "绯闻对象", "传闻",
                ) and peer.action in (
                    PRAction.APOLOGIZE, PRAction.COUNTERATTACK,
                    PRAction.PLAY_VICTIM, PRAction.STATEMENT,
                ):
                    triggered_by = peer.actor
                    trigger_relation = rel.get("relation_type")
                    break

        crisis_action = CrisisAction(
            actor=self.name,
            action=action,
            content=content,
            day=state.get("day", 0),
            triggered_by=triggered_by,
            trigger_relation=trigger_relation,
        )

        self.past_actions.append(action)
        self.memory.append(f"Day {state.get('day', 0)}: {action.label}")

        # 写入结构化记忆
        importance = 0.3
        if action in (PRAction.APOLOGIZE, PRAction.COUNTERATTACK, PRAction.COMEBACK):
            importance = 0.8
        elif action in (PRAction.STATEMENT, PRAction.GO_ON_SHOW, PRAction.LAWSUIT):
            importance = 0.6
        elif action == PRAction.SILENCE:
            importance = 0.2
        self._add_memory(
            content=f"Day {state.get('day', 0)}: {action.label}",
            source="crisis_action",
            importance=importance,
            tags=[action.value, phase.value],
            metadata={"approval": state.get("approval_scores", {}).get(self.name, 50)},
        )

        return crisis_action

    def _apply_peer_influence(
        self,
        peer_actions: list[CrisisAction],
        candidates: list[tuple[PRAction, float]],
    ) -> None:
        """根据关系类型、关系强度和对方动作，调整候选动作权重"""
        for peer_action in peer_actions:
            rels = self.kg.get_relationship_context(self.name, peer_action.actor)
            if not rels:
                continue
            rel = rels[0]
            relation_type = rel.get("relation_type", "")
            # 关系强度：默认 0.5，强关系影响更大
            strength = rel.get("strength", 0.5)

            # 配偶/家人道歉了 → 我也倾向缓和
            if relation_type in ("配偶", "伴侣", "家人", "亲属") and \
               peer_action.action == PRAction.APOLOGIZE:
                self._boost(candidates, PRAction.APOLOGIZE, 1.5 * strength)
                self._boost(candidates, PRAction.STATEMENT, 1.0 * strength)
                self._boost(candidates, PRAction.SILENCE, 0.8 * strength)

            # 配偶/家人反击了 → 我也倾向强硬
            if relation_type in ("配偶", "伴侣", "家人", "亲属") and \
               peer_action.action == PRAction.COUNTERATTACK:
                self._boost(candidates, PRAction.COUNTERATTACK, 1.2 * strength)
                self._boost(candidates, PRAction.STATEMENT, 1.5 * strength)

            # 对手反击了 → 我也倾向反击
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               peer_action.action == PRAction.COUNTERATTACK:
                self._boost(candidates, PRAction.COUNTERATTACK, 1.5 * strength)
                self._boost(candidates, PRAction.STATEMENT, 1.0 * strength)

            # 对手道歉了 → 我可以高姿态沉默
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               peer_action.action == PRAction.APOLOGIZE:
                self._boost(candidates, PRAction.SILENCE, 1.5 * strength)
                self._boost(candidates, PRAction.PLAY_VICTIM, 1.0 * strength)

            # 对手卖惨 → 我发声明澄清
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               peer_action.action == PRAction.PLAY_VICTIM:
                self._boost(candidates, PRAction.STATEMENT, 2.0 * strength)
                self._boost(candidates, PRAction.COUNTERATTACK, 1.0 * strength)

            # 被指名了 → 必须回应
            if peer_action.target == self.name:
                self._boost(candidates, PRAction.STATEMENT, 2.0)
                self._boost(candidates, PRAction.COUNTERATTACK, 1.0)

            # 绯闻对象道歉了 → 我也倾向隐退/声明
            if relation_type in ("绯闻对象", "绯闻", "传闻") and \
               peer_action.action == PRAction.APOLOGIZE:
                self._boost(candidates, PRAction.HIDE, 1.5 * strength)
                self._boost(candidates, PRAction.STATEMENT, 1.0 * strength)

            # 绯闻对象反击了 → 我倾向声明/沉默
            if relation_type in ("绯闻对象", "绯闻", "传闻") and \
               peer_action.action == PRAction.COUNTERATTACK:
                self._boost(candidates, PRAction.STATEMENT, 1.5 * strength)
                self._boost(candidates, PRAction.SILENCE, 1.0 * strength)

            # 前配偶道歉了 → 我发声明表明立场
            if relation_type in ("前配偶", "前任") and \
               peer_action.action == PRAction.APOLOGIZE:
                self._boost(candidates, PRAction.STATEMENT, 1.5 * strength)

            # 前配偶反击了 → 我倾向起诉/声明
            if relation_type in ("前配偶", "前任") and \
               peer_action.action == PRAction.COUNTERATTACK:
                self._boost(candidates, PRAction.LAWSUIT, 2.0 * strength)
                self._boost(candidates, PRAction.STATEMENT, 1.5 * strength)

    def _apply_audience_influence(
        self,
        audience_reactions: list[AgentMessage],
        candidates: list[tuple[PRAction, float]],
    ) -> None:
        """根据观众反应调整决策（含性格交叉和语义分析）"""
        if not audience_reactions:
            return

        pos = sum(1 for r in audience_reactions if r.sentiment == "positive")
        neg = sum(1 for r in audience_reactions if r.sentiment == "negative")
        total = max(1, pos + neg)
        neg_ratio = neg / total
        neuroticism = self.personality.get("neuroticism", 0.5)

        # 观众愤怒为主
        if neg_ratio > 0.6:
            if neuroticism > 0.6:
                # 高神经质 + 负面观众 → 倾向反击而非道歉
                self._boost(candidates, PRAction.COUNTERATTACK, 1.5)
                self._boost(candidates, PRAction.STATEMENT, 1.0)
            else:
                # 正常 → 倾向道歉/沉默
                self._boost(candidates, PRAction.APOLOGIZE, 1.5)
                self._boost(candidates, PRAction.SILENCE, 1.0)

        # 观众支持为主 → 倾向声明/反击
        elif neg_ratio < 0.3:
            self._boost(candidates, PRAction.STATEMENT, 1.0)
            self._boost(candidates, PRAction.COUNTERATTACK, 0.8)

        # 意见分歧区间 (0.3-0.6) → 主动表态
        else:
            self._boost(candidates, PRAction.STATEMENT, 1.0)
            self._boost(candidates, PRAction.GO_ON_SHOW, 0.8)

        # 语义分析：从观众评论中提取关键诉求
        all_content = " ".join(r.content for r in audience_reactions if r.content)
        if "道歉" in all_content or "认错" in all_content:
            self._boost(candidates, PRAction.APOLOGIZE, 0.8)
        if "解释" in all_content or "真相" in all_content or "声明" in all_content:
            self._boost(candidates, PRAction.STATEMENT, 1.0)
        if "封杀" in all_content or "滚" in all_content:
            self._boost(candidates, PRAction.HIDE, 1.0)
            self._boost(candidates, PRAction.APOLOGIZE, 0.5)
        if "起诉" in all_content or "律师" in all_content:
            self._boost(candidates, PRAction.LAWSUIT, 0.8)

    @staticmethod
    def _boost(
        candidates: list[tuple[PRAction, float]],
        target_action: PRAction,
        bonus: float,
    ) -> None:
        """给候选动作加权"""
        for i, (action, weight) in enumerate(candidates):
            if action == target_action:
                candidates[i] = (action, weight + bonus)
                return
        # 不在候选中则追加
        candidates.append((target_action, bonus))

    def _rule_decide(
        self,
        phase: CrisisPhase,
        state: dict,
        peer_actions: list[CrisisAction] | None = None,
        audience_reactions: list[AgentMessage] | None = None,
    ) -> PRAction:
        """规则模式决策 — 基于 Big Five + 扩展人格维度"""
        approval = state.get("approval_scores", {}).get(self.name, 50.0)
        heat = state.get("heat_index", 50.0)
        neuroticism = self.personality.get("neuroticism", 0.5)
        extraversion = self.personality.get("extraversion", 0.5)
        agreeableness = self.personality.get("agreeableness", 0.5)
        risk_tolerance = self.personality.get("risk_tolerance", 0.5)
        public_visibility = self.personality.get("public_visibility", 0.5)
        media_savvy = self.personality.get("media_savvy", 0.5)
        controversy_history = self.personality.get("controversy_history", 0.3)

        # 重复动作惩罚：连续做同一动作降低优先级（含语义相似组）
        recent = self.past_actions[-5:] if self.past_actions else []
        action_weights: dict[PRAction, float] = {}

        # 语义相似动作组
        SIMILAR_GROUPS: list[set[PRAction]] = [
            {PRAction.SILENCE, PRAction.HIDE},
            {PRAction.STATEMENT, PRAction.GO_ON_SHOW},
            {PRAction.APOLOGIZE, PRAction.CHARITY},
            {PRAction.COUNTERATTACK, PRAction.LAWSUIT},
        ]

        for action in PRAction:
            weight = 1.0

            # 直接重复惩罚
            repeat_count = recent.count(action)
            if repeat_count >= 3:
                weight *= 0.1
            elif repeat_count >= 2:
                weight *= 0.2
            elif repeat_count == 1:
                weight *= 0.5

            # 语义相似组惩罚
            for group in SIMILAR_GROUPS:
                if action in group:
                    group_repeats = sum(1 for a in recent if a in group)
                    if group_repeats >= 3:
                        weight *= 0.3
                    elif group_repeats >= 2:
                        weight *= 0.6

            action_weights[action] = weight

        # 核心决策矩阵
        candidates: list[tuple[PRAction, float]] = []

        # 口碑高 + 热度低 → 沉默即可
        if approval > 60 and heat < 40:
            candidates.append((PRAction.SILENCE, 3.0))
            if extraversion > 0.6:
                candidates.append((PRAction.STATEMENT, 2.0))

        # 口碑中等 + 发酵/高峰期 → 发声明或上节目
        if 30 < approval <= 60:
            candidates.append((PRAction.STATEMENT, 2.5))
            if phase in (CrisisPhase.PEAK, CrisisPhase.MITIGATION):
                candidates.append((PRAction.APOLOGIZE, 2.0 + agreeableness))
            if extraversion > 0.6 and phase not in (CrisisPhase.BREAKOUT,):
                candidates.append((PRAction.GO_ON_SHOW, 2.0 + extraversion))

        # 口碑很低 → 道歉、卖惨或法律
        if approval <= 30:
            candidates.append((PRAction.APOLOGIZE, 3.0 + agreeableness))
            candidates.append((PRAction.PLAY_VICTIM, 2.0))
            candidates.append((PRAction.HIDE, 1.5))
            candidates.append((PRAction.LAWSUIT, 1.0))

        # 神经质高 → 反击倾向
        if neuroticism > 0.7:
            candidates.append((PRAction.COUNTERATTACK, 2.5 + neuroticism))

        # ── 新增人格维度影响 ──

        # 高风险容忍 → 倾向反击/卖惨
        if risk_tolerance > 0.6:
            candidates.append((PRAction.COUNTERATTACK, 1.5 + risk_tolerance))
            candidates.append((PRAction.PLAY_VICTIM, 1.0 + risk_tolerance * 0.5))

        # 高公众可见度 → 沉默代价大，倾向主动出击
        if public_visibility > 0.7:
            self._boost(candidates, PRAction.SILENCE, -1.0)  # 降权沉默
            candidates.append((PRAction.STATEMENT, 1.5 + public_visibility))

        # 高媒体素养 → 声明/上节目效果更好
        if media_savvy > 0.6:
            candidates.append((PRAction.STATEMENT, 1.0 + media_savvy))
            if phase not in (CrisisPhase.BREAKOUT,):
                candidates.append((PRAction.GO_ON_SHOW, 1.0 + media_savvy * 0.5))

        # 高争议历史 → 谨慎为主，但神经质高时反而冲动
        if controversy_history > 0.6 and neuroticism < 0.6:
            candidates.append((PRAction.APOLOGIZE, 1.0 + controversy_history * 0.5))
            self._boost(candidates, PRAction.COUNTERATTACK, -0.5)

        # 外向 + 应对/收尾期 → 公益/复出
        if phase in (CrisisPhase.MITIGATION, CrisisPhase.RESOLUTION, CrisisPhase.AFTERMATH):
            candidates.append((PRAction.CHARITY, 2.0))
            if phase == CrisisPhase.AFTERMATH:
                candidates.append((PRAction.COMEBACK, 2.5))

        # ── 角色感知修正 ──
        if self.crisis_role == CrisisRole.PERPETRATOR:
            # 出轨方/加害者：禁止复出，不能卖惨，倾向道歉和隐退
            self._boost(candidates, PRAction.COMEBACK, -5.0)
            self._boost(candidates, PRAction.PLAY_VICTIM, -3.0)
            self._boost(candidates, PRAction.COUNTERATTACK, -2.0)
            self._boost(candidates, PRAction.HIDE, 2.0)
            self._boost(candidates, PRAction.APOLOGIZE, 1.5)
            self._boost(candidates, PRAction.SILENCE, 1.0)
            # 余波期额外禁止复出
            if phase == CrisisPhase.AFTERMATH:
                self._boost(candidates, PRAction.COMEBACK, -5.0)

        elif self.crisis_role == CrisisRole.VICTIM:
            # 受害者：发声明、起诉，不道歉，可以卖惨
            self._boost(candidates, PRAction.STATEMENT, 2.0)
            self._boost(candidates, PRAction.LAWSUIT, 1.5)
            self._boost(candidates, PRAction.APOLOGIZE, -3.0)
            self._boost(candidates, PRAction.PLAY_VICTIM, 1.0)
            self._boost(candidates, PRAction.COUNTERATTACK, -1.0)
            self._boost(candidates, PRAction.COMEBACK, 1.0)

        elif self.crisis_role == CrisisRole.ACCOMPLICE:
            # 第三者/同谋：禁止复出，不能卖惨，倾向道歉和隐退
            self._boost(candidates, PRAction.COMEBACK, -4.0)
            self._boost(candidates, PRAction.PLAY_VICTIM, -2.5)
            self._boost(candidates, PRAction.HIDE, 1.5)
            self._boost(candidates, PRAction.APOLOGIZE, 1.0)
            self._boost(candidates, PRAction.COUNTERATTACK, -1.5)

        # ── 八卦类型修正 ──
        if self.gossip_type == GossipType.CHEATING:
            # 出轨事件：加害者倾向道歉隐退，受害者倾向声明起诉
            if self.crisis_role == CrisisRole.PERPETRATOR:
                self._boost(candidates, PRAction.APOLOGIZE, 2.0)
                self._boost(candidates, PRAction.HIDE, 1.5)
                self._boost(candidates, PRAction.COUNTERATTACK, -3.0)
            elif self.crisis_role == CrisisRole.VICTIM:
                self._boost(candidates, PRAction.STATEMENT, 2.0)
                self._boost(candidates, PRAction.LAWSUIT, 1.5)
        elif self.gossip_type in (GossipType.DRUGS, GossipType.TAX_EVASION):
            # 涉毒/偷税：几乎只能隐退+公益，禁止反击
            self._boost(candidates, PRAction.HIDE, 2.5)
            self._boost(candidates, PRAction.CHARITY, 1.5)
            self._boost(candidates, PRAction.COUNTERATTACK, -5.0)
            self._boost(candidates, PRAction.PLAY_VICTIM, -3.0)
            self._boost(candidates, PRAction.COMEBACK, -4.0)
        elif self.gossip_type == GossipType.DIVORCE:
            # 离婚事件：倾向声明，各方相对中立
            self._boost(candidates, PRAction.STATEMENT, 1.5)
            self._boost(candidates, PRAction.GO_ON_SHOW, 1.0)
        elif self.gossip_type == GossipType.SCANDAL:
            # 丑闻：倾向声明+上节目澄清
            self._boost(candidates, PRAction.STATEMENT, 1.5)
            self._boost(candidates, PRAction.GO_ON_SHOW, 1.0)
            if self.crisis_role == CrisisRole.PERPETRATOR:
                self._boost(candidates, PRAction.COUNTERATTACK, -2.0)

        # ── 记忆驱动的决策修正 ──
        silence_days = self._get_consecutive_silence_days()
        if silence_days >= 3:
            # 连续沉默3天+，紧迫感提升，倾向主动出击
            self._boost(candidates, PRAction.STATEMENT, 2.0 + silence_days * 0.3)
            self._boost(candidates, PRAction.APOLOGIZE, 1.5)
            self._boost(candidates, PRAction.SILENCE, -2.0)

        apology_count = self._get_apology_count()
        if apology_count >= 2 and approval < 40:
            # 多次道歉无效，切换策略
            self._boost(candidates, PRAction.APOLOGIZE, -2.0)
            self._boost(candidates, PRAction.HIDE, 2.0)
            self._boost(candidates, PRAction.CHARITY, 1.5)

        # 高热度 → 必须有动作
        if heat > 70 and approval < 50:
            candidates.append((PRAction.STATEMENT, 3.5))
            candidates.append((PRAction.APOLOGIZE, 2.5))

        # 如果没选出合适的，给默认选项
        if not candidates:
            candidates.append((PRAction.SILENCE, 1.0))

        # 关系影响
        if peer_actions:
            self._apply_peer_influence(peer_actions, candidates)

        # 观众影响
        if audience_reactions:
            self._apply_audience_influence(audience_reactions, candidates)

        # 传播触发：如果 memory 中有 PROPAGATION 标记，提高回应倾向
        propagation_triggers = [
            m for m in self.memory
            if isinstance(m, str) and m.startswith("PROPAGATION:")
        ]
        if propagation_triggers:
            # 最近一次传播触发
            latest_trigger = propagation_triggers[-1]
            self._boost(candidates, PRAction.STATEMENT, 2.0)
            if "道歉" in latest_trigger:
                self._boost(candidates, PRAction.APOLOGIZE, 1.5)
            elif "反击" in latest_trigger:
                self._boost(candidates, PRAction.COUNTERATTACK, 1.5)
            elif "卖惨" in latest_trigger:
                self._boost(candidates, PRAction.STATEMENT, 1.5)
                self._boost(candidates, PRAction.PLAY_VICTIM, 1.0)

        # 应用权重并选择
        weighted = []
        for action, base_w in candidates:
            final_w = base_w * action_weights.get(action, 1.0)
            weighted.append((action, final_w))

        # 加一点随机性
        total = sum(w for _, w in weighted)
        r = random.uniform(0, total)
        cumulative = 0.0
        for action, w in weighted:
            cumulative += w
            if r <= cumulative:
                return action

        return weighted[-1][0]

    async def _llm_decide(
        self,
        phase: CrisisPhase,
        state: dict,
        peer_actions: list[CrisisAction] | None = None,
        audience_reactions: list[AgentMessage] | None = None,
    ) -> PRAction:
        """LLM 模式决策"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            from swarmsim.llm import get_client

            client = get_client()
            prompt = self._build_decision_prompt(phase, state, peer_actions, audience_reactions)
            logger.info(f"[LLM] {self.name} 正在请求 LLM 决策 (阶段: {phase.label})")
            response = await client.generate_async(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"[LLM] {self.name} LLM 响应: {content[:100]}")

            # 解析 LLM 返回的动作（使用正则匹配完整单词）
            action_map = {a.value: a for a in PRAction}
            for value, action in action_map.items():
                if re.search(r'\b' + re.escape(value) + r'\b', content.lower()):
                    logger.info(f"[LLM] {self.name} 选择动作: {action.label}")
                    return action

            logger.warning(f"[LLM] {self.name} 无法解析 LLM 响应，fallback 到规则模式")
            return self._rule_decide(phase, state, peer_actions, audience_reactions)

        except Exception as e:
            logger.warning(f"[LLM] {self.name} LLM 调用失败: {type(e).__name__}: {e}")
            return self._rule_decide(phase, state, peer_actions, audience_reactions)

    def _build_decision_prompt(
        self,
        phase: CrisisPhase,
        state: dict,
        peer_actions: list[CrisisAction] | None = None,
        audience_reactions: list[AgentMessage] | None = None,
    ) -> str:
        """构建 LLM 决策 prompt"""
        approval = state.get("approval_scores", {}).get(self.name, 50.0)
        heat = state.get("heat_index", 50.0)
        day = state.get("day", 0)

        actions_str = ", ".join(f"{a.value}({a.label})" for a in PRAction)
        recent = ", ".join(a.label for a in self.past_actions[-3:]) or "无"

        # 其他 Agent 今天的动作
        peer_info = ""
        if peer_actions:
            peer_lines = []
            for pa in peer_actions:
                rels = self.kg.get_relationship_context(self.name, pa.actor)
                rel_type = rels[0].get("relation_type", "未知关系") if rels else "未知关系"
                peer_lines.append(f"  {pa.actor}(关系:{rel_type})做了:{pa.action.label}")
            peer_info = f"\n今天其他人已经采取的动作：\n" + "\n".join(peer_lines) + "\n"

        # 观众反应
        audience_info = ""
        if audience_reactions:
            pos = sum(1 for r in audience_reactions if r.sentiment == "positive")
            neg = sum(1 for r in audience_reactions if r.sentiment == "negative")
            neu = sum(1 for r in audience_reactions if r.sentiment == "neutral")
            sample = [r.content for r in audience_reactions[:3] if r.content]
            audience_info = f"\n观众反应：正面{pos}条，负面{neg}条，中性{neu}条\n"
            if sample:
                audience_info += "观众评论示例：" + "；".join(sample) + "\n"

        # 角色上下文
        role_context = ""
        if self.crisis_role == CrisisRole.PERPETRATOR:
            role_context = "你是这场危机的主要过错方，公众认为你犯下了严重错误。你不应该尝试复出或卖惨。"
        elif self.crisis_role == CrisisRole.VICTIM:
            role_context = "你是这场危机的受害者，公众对你表示同情。你不需要道歉。"
        elif self.crisis_role == CrisisRole.ACCOMPLICE:
            role_context = "你是这场危机的关联当事人（第三者/同谋），公众对你持负面看法。你不应该复出或卖惨。"
        if self.gossip_type:
            role_context += f"\n这是一起{self.gossip_type.label}事件。"

        # 图谱上下文
        graph_context = ""
        try:
            graph_context = self.kg.to_context_string(self.name, max_chars=500)
            if graph_context:
                graph_context = f"\n你的社会关系网络：\n{graph_context}\n"
        except Exception:
            pass

        # 历史事件摘要
        timeline_summary = ""
        try:
            events = self.kg.get_person_timeline(self.name)
            important_events = sorted(
                events, key=lambda e: e.get("importance", 0.3), reverse=True
            )[:3]
            if important_events:
                lines = [f"  - {e.get('title', '')} ({e.get('date', '')})" for e in important_events]
                timeline_summary = "\n你的重要历史事件：\n" + "\n".join(lines) + "\n"
        except Exception:
            pass

        # 记忆摘要
        memory_summary = ""
        recent_memories = self._get_recent_memories(n=5)
        if recent_memories:
            mem_lines = [f"  - {m.content}" for m in recent_memories]
            memory_summary = "\n你最近的记忆：\n" + "\n".join(mem_lines) + "\n"

        # 性格自然语言描述
        personality_desc = self._describe_personality()

        return (
            f"你是明星{self.name}，正面临公关危机。\n"
            f"{role_context}\n"
            f"当前第{day}天，阶段：{phase.label}，"
            f"你的口碑分：{approval:.0f}/100，舆情热度：{heat:.0f}/100。\n"
            f"你的性格：{personality_desc}\n"
            f"最近动作：{recent}\n"
            f"{graph_context}{timeline_summary}{memory_summary}"
            f"{peer_info}{audience_info}"
            f"可选动作：{actions_str}\n"
            f"请从可选动作中选择一个，只回复动作的英文value。"
        )

    def _describe_personality(self) -> str:
        """将性格数值转为自然语言描述"""
        p = self.personality
        parts = []

        o = p.get("openness", 0.5)
        c = p.get("conscientiousness", 0.5)
        e = p.get("extraversion", 0.5)
        a = p.get("agreeableness", 0.5)
        n = p.get("neuroticism", 0.5)

        if e > 0.7: parts.append("外向活泼，善于社交")
        elif e < 0.3: parts.append("内向低调，不善社交")

        if n > 0.7: parts.append("情绪波动大，容易冲动")
        elif n < 0.3: parts.append("情绪稳定，冷静理性")

        if a > 0.7: parts.append("温和随和，善于合作")
        elif a < 0.3: parts.append("强硬好斗，不易妥协")

        if c > 0.7: parts.append("严谨负责，做事有计划")
        elif c < 0.3: parts.append("随性散漫")

        risk = p.get("risk_tolerance", 0.5)
        if risk > 0.7: parts.append("敢于冒险")
        elif risk < 0.3: parts.append("谨慎保守")

        vis = p.get("public_visibility", 0.5)
        if vis > 0.8: parts.append("顶流明星，公众关注度极高")
        elif vis < 0.3: parts.append("知名度一般")

        controversy = p.get("controversy_history", 0.3)
        if controversy > 0.7: parts.append("过往争议较多")

        return "；".join(parts) if parts else "性格中等，无明显特征"

    def get_action_description(self, action: PRAction) -> str:
        """获取动作的中文描述"""
        return ACTION_DESCRIPTIONS.get(action, "").format(name=self.name)

    def reset(self):
        self.memory.clear()
        self.past_actions.clear()
        self._memory_store.clear_agent(self.name)
        self.crisis_role = CrisisRole.BYSTANDER
        self.gossip_type = None

    # ── 记忆管理 ──

    def _add_memory(
        self,
        content: str,
        source: str = "action",
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """写入结构化记忆"""
        from datetime import datetime
        self._memory_counter += 1
        entry = MemoryEntry(
            id=f"{self.name}_{self._memory_counter}",
            agent_id=self.name,
            timestamp=datetime.now(),
            content=content,
            source=source,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._memory_store.add(entry)
        # 同步写入简易 memory（保留兼容性）
        self.memory.append(content)

    def _get_recent_memories(self, n: int = 5) -> list[MemoryEntry]:
        """获取最近的记忆"""
        return self._memory_store.get_recent(self.name, n=n)

    def _get_important_memories(self, n: int = 5) -> list[MemoryEntry]:
        """获取最重要的记忆"""
        return self._memory_store.get_important(self.name, n=n)

    def _get_consecutive_silence_days(self) -> int:
        """计算连续沉默天数"""
        recent = self._get_recent_memories(n=10)
        count = 0
        for m in reversed(recent):
            if "SILENCE" in m.content or "HIDE" in m.content:
                count += 1
            else:
                break
        return count

    def _get_apology_count(self, n: int = 5) -> int:
        """获取最近 N 条记忆中道歉的次数"""
        recent = self._get_recent_memories(n=n)
        return sum(1 for m in recent if "APOLOGIZE" in m.content or "道歉" in m.content)

    # ── 自由互动模式 ──

    async def generate_free_response(
        self,
        state: dict,
        peer_actions: list[CrisisAction] | None = None,
        audience_reactions: list[AgentMessage] | None = None,
    ) -> CrisisAction:
        """自由互动模式下的决策

        Args:
            state: 当前仿真状态
            peer_actions: 其他 Agent 今天的动作
            audience_reactions: 观众反应

        Returns:
            CrisisAction (free_action 字段填充)
        """
        peer_actions = peer_actions or []
        audience_reactions = audience_reactions or []

        if self.use_llm:
            free_action = await self._llm_decide_free(state, peer_actions, audience_reactions)
        else:
            free_action = self._rule_decide_free(state, peer_actions, audience_reactions)

        from swarmsim.crisis.models import PRAction

        content = FREE_ACTION_DESCRIPTIONS.get(free_action, "").format(name=self.name)

        # 使用 SILENCE 作为自由模式的 PRAction 占位
        crisis_action = CrisisAction(
            actor=self.name,
            action=PRAction.SILENCE,
            free_action=free_action,
            content=content,
            day=state.get("day", 0),
        )

        self.past_actions.append(PRAction.SILENCE)
        self.memory.append(f"Day {state.get('day', 0)}: [自由]{free_action.label}")

        # 写入结构化记忆
        importance = 0.4
        if free_action in (FreeAction.CRITICIZE, FreeAction.RUMOR, FreeAction.ANNOUNCE):
            importance = 0.7
        elif free_action in (FreeAction.SUPPORT, FreeAction.MEDIATE):
            importance = 0.6
        elif free_action == FreeAction.IGNORE:
            importance = 0.2
        self._add_memory(
            content=f"Day {state.get('day', 0)}: [自由]{free_action.label}",
            source="free_action",
            importance=importance,
            tags=[free_action.value],
            metadata={"approval": state.get("approval_scores", {}).get(self.name, 50)},
        )

        return crisis_action

    def _rule_decide_free(
        self,
        state: dict,
        peer_actions: list[CrisisAction],
        audience_reactions: list[AgentMessage],
    ) -> FreeAction:
        """规则模式自由互动决策"""
        neuroticism = self.personality.get("neuroticism", 0.5)
        extraversion = self.personality.get("extraversion", 0.5)
        agreeableness = self.personality.get("agreeableness", 0.5)
        risk_tolerance = self.personality.get("risk_tolerance", 0.5)
        openness = self.personality.get("openness", 0.5)

        candidates: list[tuple[FreeAction, float]] = []

        # 性格驱动
        if extraversion > 0.6:
            candidates.append((FreeAction.SPEAK, 2.0 + extraversion))
            candidates.append((FreeAction.SOCIALIZE, 1.5))
        if agreeableness > 0.6:
            candidates.append((FreeAction.SUPPORT, 2.0 + agreeableness))
            candidates.append((FreeAction.MEDIATE, 1.5))
        if neuroticism > 0.6:
            candidates.append((FreeAction.CRITICIZE, 1.0 + neuroticism))
            candidates.append((FreeAction.RUMOR, 0.5 + neuroticism * 0.5))
        if risk_tolerance > 0.6:
            candidates.append((FreeAction.ANNOUNCE, 1.5 + risk_tolerance))
            candidates.append((FreeAction.RUMOR, 1.0 + risk_tolerance * 0.3))
        if openness > 0.6:
            candidates.append((FreeAction.COLLABORATE, 1.5 + openness))
        if extraversion < 0.3:
            candidates.append((FreeAction.IGNORE, 2.0))
            candidates.append((FreeAction.RETREAT, 1.5))

        # 关系驱动
        for pa in peer_actions:
            rels = self.kg.get_relationship_context(self.name, pa.actor)
            if not rels:
                continue
            rel_type = rels[0].get("relation_type", "")

            if rel_type in ("配偶", "伴侣", "好友", "闺蜜"):
                candidates.append((FreeAction.SUPPORT, 3.0))
                candidates.append((FreeAction.PRIVATE_MSG, 2.0))
            if rel_type in ("对手", "宿敌", "竞争对手", "同代竞争"):
                candidates.append((FreeAction.CRITICIZE, 2.5))
                if pa.free_action and pa.free_action == FreeAction.CRITICIZE:
                    candidates.append((FreeAction.CRITICIZE, 3.5))
            if rel_type in ("合作", "搭档", "合作伙伴"):
                candidates.append((FreeAction.COLLABORATE, 3.0))

        # 观众驱动
        if audience_reactions:
            neg = sum(1 for r in audience_reactions if r.sentiment == "negative")
            total = max(1, len(audience_reactions))
            if neg / total > 0.6:
                candidates.append((FreeAction.RETREAT, 2.0))
                candidates.append((FreeAction.IGNORE, 1.5))

        if not candidates:
            candidates.append((FreeAction.IGNORE, 1.0))

        # 加权随机选择
        total_w = sum(w for _, w in candidates)
        r = random.uniform(0, total_w)
        cumulative = 0.0
        for action, w in candidates:
            cumulative += w
            if r <= cumulative:
                return action
        return candidates[-1][0]

    async def _llm_decide_free(
        self,
        state: dict,
        peer_actions: list[CrisisAction],
        audience_reactions: list[AgentMessage],
    ) -> FreeAction:
        """LLM 模式自由互动决策"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            from swarmsim.llm import get_client

            client = get_client()
            actions_str = ", ".join(f"{a.value}({a.label})" for a in FreeAction)

            peer_info = ""
            if peer_actions:
                lines = []
                for pa in peer_actions:
                    rels = self.kg.get_relationship_context(self.name, pa.actor)
                    rel_type = rels[0].get("relation_type", "未知") if rels else "未知"
                    action_text = pa.free_action.label if pa.free_action else pa.action.label
                    lines.append(f"  {pa.actor}(关系:{rel_type})做了:{action_text}")
                peer_info = "\n其他人今天的动作：\n" + "\n".join(lines)

            # 角色上下文
            role_context = ""
            if self.crisis_role == CrisisRole.PERPETRATOR:
                role_context = "你是这场危机的主要过错方。"
            elif self.crisis_role == CrisisRole.VICTIM:
                role_context = "你是这场危机的受害者。"
            elif self.crisis_role == CrisisRole.ACCOMPLICE:
                role_context = "你是这场危机的关联当事人。"
            if self.gossip_type:
                role_context += f" 这是一起{self.gossip_type.label}事件。"

            approval = state.get("approval_scores", {}).get(self.name, 50.0)
            heat = state.get("heat_index", 50.0)
            personality_desc = self._describe_personality()
            recent = ", ".join(a.label for a in self.past_actions[-3:]) or "无"

            # 观众反应
            audience_info = ""
            if audience_reactions:
                pos = sum(1 for r in audience_reactions if r.sentiment == "positive")
                neg = sum(1 for r in audience_reactions if r.sentiment == "negative")
                audience_info = f"\n观众反应：正面{pos}条，负面{neg}条。\n"

            prompt = (
                f"你是明星{self.name}，处于自由互动模式。\n"
                f"{role_context}\n"
                f"第{state.get('day', 0)}天，口碑分：{approval:.0f}/100，"
                f"舆情热度：{heat:.0f}/100。\n"
                f"你的性格：{personality_desc}\n"
                f"最近动作：{recent}\n"
                f"{peer_info}{audience_info}"
                f"可选动作：{actions_str}\n"
                f"请只回复动作的英文value。"
            )

            response = await client.generate_async(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            action_map = {a.value: a for a in FreeAction}
            for value, action in action_map.items():
                if re.search(r'\b' + re.escape(value) + r'\b', content.lower()):
                    return action

            return self._rule_decide_free(state, peer_actions, audience_reactions)

        except Exception as e:
            logger.warning(f"[LLM] {self.name} 自由模式调用失败: {e}")
            return self._rule_decide_free(state, peer_actions, audience_reactions)

