# -*- coding: utf-8 -*-
"""
明星 Agent - 从 GraphRAG 构建人设

支持纯规则模式（无需 API key）和 LLM 模式。
规则模式基于 Big Five 性格特质和状态矩阵决策。
"""

from __future__ import annotations

import random
from typing import Any

from swarmsim.crisis.models import CrisisPhase, PRAction, CrisisAction
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

    def generate_crisis_response(
        self,
        phase: CrisisPhase,
        state: dict,
        forced_action: PRAction | None = None,
    ) -> CrisisAction:
        """生成危机响应动作

        Args:
            phase: 当前危机阶段
            state: 当前仿真状态 {approval_scores, heat_index, ...}
            forced_action: 干预系统强制动作

        Returns:
            CrisisAction
        """
        if forced_action:
            action = forced_action
        elif self.use_llm:
            action = self._llm_decide(phase, state)
        else:
            action = self._rule_decide(phase, state)

        content = ACTION_DESCRIPTIONS.get(action, "").format(name=self.name)

        crisis_action = CrisisAction(
            actor=self.name,
            action=action,
            content=content,
            day=state.get("day", 0),
        )

        self.past_actions.append(action)
        self.memory.append(f"Day {state.get('day', 0)}: {action.label}")

        return crisis_action

    def _rule_decide(self, phase: CrisisPhase, state: dict) -> PRAction:
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

    def _llm_decide(self, phase: CrisisPhase, state: dict) -> PRAction:
        """LLM 模式决策"""
        try:
            from swarmsim.llm import get_client

            client = get_client()
            prompt = self._build_decision_prompt(phase, state)
            response = client.generate(prompt)

            # 解析 LLM 返回的动作
            action_map = {a.value: a for a in PRAction}
            for value, action in action_map.items():
                if value in response.lower():
                    return action

            # fallback
            return self._rule_decide(phase, state)

        except Exception:
            return self._rule_decide(phase, state)

    def _build_decision_prompt(self, phase: CrisisPhase, state: dict) -> str:
        """构建 LLM 决策 prompt"""
        approval = state.get("approval_scores", {}).get(self.name, 50.0)
        heat = state.get("heat_index", 50.0)
        day = state.get("day", 0)

        actions_str = ", ".join(f"{a.value}({a.label})" for a in PRAction)
        recent = ", ".join(a.label for a in self.past_actions[-3:]) or "无"

        return (
            f"你是明星{self.name}，正面临公关危机。\n"
            f"当前第{day}天，阶段：{phase.label}，"
            f"你的口碑分：{approval:.0f}/100，舆情热度：{heat:.0f}/100。\n"
            f"你的性格特质：{self.personality}\n"
            f"最近动作：{recent}\n"
            f"可选动作：{actions_str}\n"
            f"请从可选动作中选择一个，只回复动作的英文value。"
        )

    def get_action_description(self, action: PRAction) -> str:
        """获取动作的中文描述"""
        return ACTION_DESCRIPTIONS.get(action, "").format(name=self.name)

    def reset(self):
        self.memory.clear()
        self.past_actions.clear()
