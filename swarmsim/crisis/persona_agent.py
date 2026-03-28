# -*- coding: utf-8 -*-
"""
明星 Agent - 从 GraphRAG 构建人设

支持纯规则模式（无需 API key）和 LLM 模式。
规则模式基于 Big Five 性格特质和状态矩阵决策。
"""

from __future__ import annotations

import random
from typing import Any

from swarmsim.crisis.models import CrisisPhase, PRAction, CrisisAction, AgentMessage
from swarmsim.graph.temporal import TemporalKnowledgeGraph


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


class CelebrityPersonaAgent:
    """从 GraphRAG 构建人设的明星 Agent"""

    def __init__(
        self,
        name: str,
        kg: TemporalKnowledgeGraph,
        use_llm: bool = False,
    ):
        self.name = name
        self.kg = kg
        self.use_llm = use_llm

        # 从图谱构建性格画像 (Big Five)
        self.personality = self._build_personality()

        # 记忆缓冲（最近事件）
        self.memory: list[str] = []
        self.past_actions: list[PRAction] = []

    def _build_personality(self) -> dict[str, float]:
        """从图谱推断 Big Five 性格特质"""
        node_id = f"celebrity:{self.name}"
        if not self.kg._graph.has_node(node_id):
            return {
                "openness": 0.5, "conscientiousness": 0.5,
                "extraversion": 0.5, "agreeableness": 0.5,
                "neuroticism": 0.5,
            }

        data = dict(self.kg._graph.nodes[node_id])
        bio = str(data.get("biography", ""))
        occupation = data.get("occupation", [])
        if isinstance(occupation, str):
            occupation = [occupation]

        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }

        # 基于职业推断
        if any(kw in " ".join(occupation) for kw in ["歌手", "偶像", "主持人"]):
            traits["extraversion"] = random.uniform(0.6, 0.85)
            traits["openness"] = random.uniform(0.6, 0.8)
        if any(kw in " ".join(occupation) for kw in ["演员", "影帝", "影后"]):
            traits["openness"] = random.uniform(0.5, 0.75)
            traits["conscientiousness"] = random.uniform(0.55, 0.8)
        if any(kw in " ".join(occupation) for kw in ["导演", "制片"]):
            traits["conscientiousness"] = random.uniform(0.6, 0.85)

        # 基于 bio 关键词
        if any(kw in bio for kw in ["争议", "负面", "封杀", "出轨"]):
            traits["neuroticism"] = random.uniform(0.55, 0.8)
            traits["agreeableness"] = random.uniform(0.3, 0.5)
        if any(kw in bio for kw in ["慈善", "公益", "温暖", "人缘好"]):
            traits["agreeableness"] = random.uniform(0.65, 0.85)
        if any(kw in bio for kw in ["低调", "内敛", "沉默"]):
            traits["extraversion"] = random.uniform(0.2, 0.4)

        # 根据历史事件类型调整
        events = self.kg.get_person_timeline(self.name)
        for event in events:
            etype = event.get("type", "")
            if etype == "gossip":
                gossip_type = event.get("gossip_type", "other")
                if gossip_type in ("cheating", "scandal"):
                    traits["neuroticism"] = max(traits["neuroticism"], 0.6)
                if gossip_type == "divorce":
                    traits["neuroticism"] = max(traits["neuroticism"], 0.55)

        return traits

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

        return crisis_action

    def _apply_peer_influence(
        self,
        peer_actions: list[CrisisAction],
        candidates: list[tuple[PRAction, float]],
    ) -> None:
        """根据关系类型和对方动作，调整候选动作权重"""
        for peer_action in peer_actions:
            rels = self.kg.get_relationship_context(self.name, peer_action.actor)
            if not rels:
                continue
            relation_type = rels[0].get("relation_type", "")

            # 配偶/家人道歉了 → 我也倾向缓和
            if relation_type in ("配偶", "伴侣", "家人", "亲属") and \
               peer_action.action == PRAction.APOLOGIZE:
                self._boost(candidates, PRAction.APOLOGIZE, 1.5)
                self._boost(candidates, PRAction.STATEMENT, 1.0)
                self._boost(candidates, PRAction.SILENCE, 0.8)

            # 配偶/家人反击了 → 我也倾向强硬
            if relation_type in ("配偶", "伴侣", "家人", "亲属") and \
               peer_action.action == PRAction.COUNTERATTACK:
                self._boost(candidates, PRAction.COUNTERATTACK, 1.2)
                self._boost(candidates, PRAction.STATEMENT, 1.5)

            # 对手反击了 → 我也倾向反击
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               peer_action.action == PRAction.COUNTERATTACK:
                self._boost(candidates, PRAction.COUNTERATTACK, 1.5)
                self._boost(candidates, PRAction.STATEMENT, 1.0)

            # 对手道歉了 → 我可以高姿态沉默
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               peer_action.action == PRAction.APOLOGIZE:
                self._boost(candidates, PRAction.SILENCE, 1.5)
                self._boost(candidates, PRAction.PLAY_VICTIM, 1.0)

            # 对手卖惨 → 我发声明澄清
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               peer_action.action == PRAction.PLAY_VICTIM:
                self._boost(candidates, PRAction.STATEMENT, 2.0)
                self._boost(candidates, PRAction.COUNTERATTACK, 1.0)

            # 被指名了 → 必须回应
            if peer_action.target == self.name:
                self._boost(candidates, PRAction.STATEMENT, 2.0)
                self._boost(candidates, PRAction.COUNTERATTACK, 1.0)

    def _apply_audience_influence(
        self,
        audience_reactions: list[AgentMessage],
        candidates: list[tuple[PRAction, float]],
    ) -> None:
        """根据观众反应调整决策"""
        if not audience_reactions:
            return

        pos = sum(1 for r in audience_reactions if r.sentiment == "positive")
        neg = sum(1 for r in audience_reactions if r.sentiment == "negative")
        total = max(1, pos + neg)
        neg_ratio = neg / total

        # 观众愤怒为主 → 倾向道歉/沉默
        if neg_ratio > 0.6:
            self._boost(candidates, PRAction.APOLOGIZE, 1.5)
            self._boost(candidates, PRAction.SILENCE, 1.0)

        # 观众支持为主 → 倾向声明/反击
        elif neg_ratio < 0.3:
            self._boost(candidates, PRAction.STATEMENT, 1.0)
            self._boost(candidates, PRAction.COUNTERATTACK, 0.8)

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
        """规则模式决策"""
        approval = state.get("approval_scores", {}).get(self.name, 50.0)
        heat = state.get("heat_index", 50.0)
        neuroticism = self.personality.get("neuroticism", 0.5)
        extraversion = self.personality.get("extraversion", 0.5)
        agreeableness = self.personality.get("agreeableness", 0.5)

        # 重复动作惩罚：连续做同一动作降低优先级
        recent = self.past_actions[-3:] if self.past_actions else []
        action_weights: dict[PRAction, float] = {}

        for action in PRAction:
            weight = 1.0

            # 重复降权
            repeat_count = recent.count(action)
            if repeat_count >= 2:
                weight *= 0.2
            elif repeat_count == 1:
                weight *= 0.5

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

        # 外向 + 应对/收尾期 → 公益/复出
        if phase in (CrisisPhase.MITIGATION, CrisisPhase.RESOLUTION, CrisisPhase.AFTERMATH):
            candidates.append((PRAction.CHARITY, 2.0))
            if phase == CrisisPhase.AFTERMATH:
                candidates.append((PRAction.COMEBACK, 2.5))

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

            # 解析 LLM 返回的动作
            action_map = {a.value: a for a in PRAction}
            for value, action in action_map.items():
                if value in content.lower():
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

        return (
            f"你是明星{self.name}，正面临公关危机。\n"
            f"当前第{day}天，阶段：{phase.label}，"
            f"你的口碑分：{approval:.0f}/100，舆情热度：{heat:.0f}/100。\n"
            f"你的性格特质：{self.personality}\n"
            f"最近动作：{recent}\n"
            f"{peer_info}{audience_info}"
            f"可选动作：{actions_str}\n"
            f"请从可选动作中选择一个，只回复动作的英文value。"
        )

    def get_action_description(self, action: PRAction) -> str:
        """获取动作的中文描述"""
        return ACTION_DESCRIPTIONS.get(action, "").format(name=self.name)

    def reset(self):
        self.memory.clear()
        self.past_actions.clear()
