# -*- coding: utf-8 -*-
"""
危机仿真引擎 - 场景加载与仿真运行

CrisisScenarioEngine: 从时序 GraphRAG 加载场景
CrisisSimulation: 单次危机仿真运行（核心循环）
"""

from __future__ import annotations

import random
from typing import Any

from swarmsim.crisis.models import (
    CrisisPhase, PRAction, GossipType, InteractionMode,
    CrisisScenario, CrisisAction, CrisisState,
    InterventionCondition, TrendingTopic, MediaHeadline, BrandStatus,
    AgentMessage, FreeAction,
)
from swarmsim.crisis.timeline import CrisisTimeline
from swarmsim.crisis.action_space import CrisisActionSpace, FreeActionSpace
from swarmsim.crisis.persona_agent import CelebrityPersonaAgent
from swarmsim.crisis.intervention import InterventionSystem
from swarmsim.crisis.vacuum_detector import InformationVacuumDetector
from swarmsim.crisis.message_bus import MessageBus
from swarmsim.crisis.audience import AudiencePool
from swarmsim.graph.temporal import TemporalKnowledgeGraph


# ── 历史基线数据 ──

HISTORICAL_OUTCOMES: dict[str, dict] = {
    "夜宿门": {
        "李小璐": {"final_approval": 20, "fate": "退出主流影视圈", "brand_status": "全部解约"},
        "PG One": {"final_approval": 5, "fate": "被全面封杀", "brand_status": "全部解约"},
        "贾乃亮": {"final_approval": 70, "fate": "转型直播带货，口碑回升", "brand_status": "部分保留"},
    },
    "做头发事件": {
        "李小璐": {"final_approval": 20, "fate": "退出主流影视圈", "brand_status": "全部解约"},
        "PG One": {"final_approval": 5, "fate": "被全面封杀", "brand_status": "全部解约"},
        "贾乃亮": {"final_approval": 70, "fate": "转型直播带货，口碑回升", "brand_status": "部分保留"},
    },
}


# ── 热搜模板 ──

TRENDING_TEMPLATES: dict[str, list[str]] = {
    CrisisPhase.BREAKOUT: [
        "#{person}事件曝光", "#{person}上热搜了", "#{person}怎么了",
        "#{person}被拍到", "#{person}大瓜",
    ],
    CrisisPhase.ESCALATION: [
        "#{person}后续", "#{person}更多细节曝光", "#{person}疑似回应",
        "#{person}粉丝崩溃", "#{person}代言危机",
    ],
    CrisisPhase.PEAK: [
        "#{person}最新回应", "#{person}事业凉凉?", "#{person}品牌解约",
        "#{person}当事人发声", "#{person}全网讨论",
    ],
    CrisisPhase.MITIGATION: [
        "#{person}道歉", "#{person}公益", "#{person}律师声明",
        "#{person}复出?", "#{person}近况",
    ],
    CrisisPhase.RESOLUTION: [
        "#{person}事件后续", "#{person}近况", "#{person}低调现身",
    ],
    CrisisPhase.AFTERMATH: [
        "#{person}现状", "#{person}转型", "#{person}粉丝态度",
    ],
}


# ── 媒体标题模板 ──

MEDIA_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    CrisisPhase.BREAKOUT: [
        ("娱乐头条", "爆料：{person}深夜被拍到{action}"),
        ("自媒体", "震惊！{person}疑似{action}"),
        ("官媒", "关注{person}事件进展"),
    ],
    CrisisPhase.ESCALATION: [
        ("娱乐头条", "更多细节：{person}{action}内幕"),
        ("自媒体", "{person}事件持续发酵，网友炸了"),
        ("八卦号", "知情人爆料{person}更多猛料"),
    ],
    CrisisPhase.PEAK: [
        ("官媒", "评{person}事件：公众人物应以身作则"),
        ("娱乐头条", "{person}{action}事件全面回顾"),
        ("财经媒体", "{person}商业版图受冲击"),
    ],
    CrisisPhase.MITIGATION: [
        ("娱乐头条", "{person}{action}试图挽回形象"),
        ("自媒体", "{person}公关策略分析"),
    ],
    CrisisPhase.RESOLUTION: [
        ("娱乐头条", "{person}事件渐趋平静"),
        ("自媒体", "{person}事件对行业的影响"),
    ],
    CrisisPhase.AFTERMATH: [
        ("娱乐头条", "{person}近况：{action}"),
        ("自媒体", "回顾{person}事件，有什么启示"),
    ],
}


class CrisisScenarioEngine:
    """从时序 GraphRAG 加载场景并创建仿真"""

    def __init__(self, kg: TemporalKnowledgeGraph):
        self.kg = kg
        self.available_scenarios: dict[str, CrisisScenario] = {}
        self._load_scenarios()

    def _load_scenarios(self) -> None:
        """从图谱加载所有可用危机场景"""
        for scenario_data in self.kg.list_crisis_scenarios(min_importance=0.3):
            title = scenario_data["title"]
            gossip_type_str = scenario_data.get("gossip_type", "other")
            try:
                gossip_type = GossipType(gossip_type_str)
            except ValueError:
                gossip_type = GossipType.OTHER

            involved = scenario_data.get("involved_persons", [])
            historical = HISTORICAL_OUTCOMES.get(title, {})

            # 构建危机前关系
            pre_rels = []
            for person in involved:
                timeline = self.kg.get_person_timeline(person)
                for event in timeline:
                    if event.get("type") == "gossip" and event.get("title") != title:
                        pre_rels.append({
                            "person": person,
                            "event": event.get("title", ""),
                            "date": event.get("date", ""),
                        })

            scenario = CrisisScenario(
                scenario_id=f"crisis_{title}",
                title=title,
                crisis_date=scenario_data.get("date", ""),
                description=f"{title} - 涉及{', '.join(involved)}",
                involved_persons=involved,
                initial_severity=scenario_data.get("importance", 0.5),
                gossip_type=gossip_type,
                historical_outcome=historical,
                pre_crisis_relationships=pre_rels,
            )
            self.available_scenarios[title] = scenario

    def list_scenarios(self) -> list[dict]:
        """列出所有可用场景"""
        results = []
        for scenario in self.available_scenarios.values():
            results.append({
                "title": scenario.title,
                "date": scenario.crisis_date,
                "importance": scenario.initial_severity,
                "gossip_type": scenario.gossip_type.value,
                "involved_persons": scenario.involved_persons,
                "has_historical": bool(scenario.historical_outcome),
            })
        results.sort(key=lambda x: x["importance"], reverse=True)
        return results

    def create_simulation(
        self,
        scenario_title: str,
        use_llm: bool = True,
        total_days: int = 30,
        interventions: list[InterventionCondition] | None = None,
    ) -> CrisisSimulation:
        """创建仿真实例"""
        scenario = self.available_scenarios.get(scenario_title)
        if not scenario:
            raise ValueError(f"未找到场景: {scenario_title}")

        return CrisisSimulation(
            scenario=scenario,
            kg=self.kg,
            use_llm=use_llm,
            total_days=total_days,
            interventions=interventions,
        )

    def create_custom_scenario(
        self,
        title: str,
        description: str,
        involved_persons: list[str],
        initial_severity: float = 0.5,
        gossip_type: str = "other",
        interaction_mode: str = "crisis",
    ) -> CrisisScenario:
        """创建自定义场景

        Args:
            title: 场景标题
            description: 场景描述
            involved_persons: 涉及的明星列表
            initial_severity: 初始严重度 0-1
            gossip_type: 八卦类型
            interaction_mode: 交互模式 (crisis/free)

        Returns:
            CrisisScenario 实例
        """
        # 验证所有人在图谱中存在
        valid_persons = []
        for name in involved_persons:
            node_id = f"celebrity:{name}"
            if self.kg._graph.has_node(node_id):
                valid_persons.append(name)

        if not valid_persons:
            raise ValueError("至少需要一个在图谱中存在的明星")

        try:
            gt = GossipType(gossip_type)
        except ValueError:
            gt = GossipType.OTHER

        try:
            mode = InteractionMode(interaction_mode)
        except ValueError:
            mode = InteractionMode.CRISIS

        # 自动发现关系
        pre_rels = self.discover_relationships(valid_persons)

        scenario = CrisisScenario(
            scenario_id=f"custom_{title}",
            title=title,
            crisis_date="2025-01-01",
            description=description,
            involved_persons=valid_persons,
            initial_severity=initial_severity,
            gossip_type=gt,
            historical_outcome={},
            pre_crisis_relationships=pre_rels,
            is_custom=True,
            interaction_mode=mode,
        )

        # 注册到可用场景
        self.available_scenarios[title] = scenario
        return scenario

    def discover_relationships(self, persons: list[str]) -> list[dict]:
        """自动发现选定名人之间的关系"""
        rels = []
        seen = set()
        for i, name_a in enumerate(persons):
            for name_b in persons[i + 1:]:
                pair = tuple(sorted([name_a, name_b]))
                if pair in seen:
                    continue
                seen.add(pair)
                context = self.kg.get_relationship_context(name_a, name_b)
                for r in context:
                    rels.append({
                        "person_a": name_a,
                        "person_b": name_b,
                        "relation_type": r.get("relation_type", "未知"),
                        "strength": r.get("strength", 0.5),
                        "confidence": r.get("confidence", 0.5),
                    })
        return rels

    def get_celebrities(self) -> list[dict]:
        """获取图谱中所有名人（供前端选择器使用）"""
        result = []
        for node_id, data in self.kg._graph.nodes(data=True):
            if data.get("node_type") != "celebrity":
                continue
            name = data.get("name", "")
            occupation = data.get("occupation", [])
            if isinstance(occupation, str):
                occupation = [occupation]
            fans = data.get("weibo_followers", 0) or 0
            works = data.get("famous_works", []) or []
            result.append({
                "name": name,
                "occupation": occupation,
                "weibo_followers": fans,
                "famous_works": works[:5],
            })
        result.sort(key=lambda x: x["weibo_followers"], reverse=True)
        return result


class CrisisSimulation:
    """单次危机仿真运行"""

    def __init__(
        self,
        scenario: CrisisScenario,
        kg: TemporalKnowledgeGraph,
        use_llm: bool = True,
        total_days: int = 30,
        interventions: list[InterventionCondition] | None = None,
    ):
        self.scenario = scenario
        self.kg = kg

        # 时间线
        start = scenario.crisis_date or "2024-01-01"
        self.timeline = CrisisTimeline(start, total_days=total_days)

        # Agent
        self.agents: dict[str, CelebrityPersonaAgent] = {}
        for name in scenario.involved_persons:
            self.agents[name] = CelebrityPersonaAgent(name, kg, use_llm=use_llm)

        # 子系统
        self.action_space = CrisisActionSpace()
        self.free_action_space = FreeActionSpace()
        self.intervention_system = InterventionSystem()
        if interventions:
            self.intervention_system.add_interventions(interventions)

        self.vacuum_detector = InformationVacuumDetector()
        self.message_bus = MessageBus()
        self.audience_pool = AudiencePool(
            scenario.involved_persons, pool_size=30,
        )

        # 状态
        self.state_history: list[CrisisState] = []
        self.current_state = self._init_state()
        self._finished = False

    def _init_state(self) -> CrisisState:
        """初始化状态"""
        approval = {}
        brands = {}
        person_brands = {}

        for name in self.scenario.involved_persons:
            # 基础口碑：从图谱数据推算（危机前的公众形象）
            base_approval = self._estimate_base_approval(name)
            # 危机冲击：严重度越高，口碑跌得越狠
            crisis_penalty = self.scenario.initial_severity * 30
            approval[name] = round(
                max(15, base_approval - crisis_penalty + random.uniform(-3, 3)), 1
            )

            # 品牌价值：基础口碑 × 0.8 + 随机波动
            brands[name] = round(
                max(20, base_approval * 0.8 + random.uniform(-3, 3)), 1
            )

            # 品牌列表
            brand_names = ["某品牌A", "某品牌B", "某品牌C"]
            person_brands[name] = [
                BrandStatus(
                    brand=b,
                    action="monitoring",
                    value=brands[name],
                )
                for b in brand_names[: random.randint(1, 3)]
            ]

        initial_heat = 40 + self.scenario.initial_severity * 40

        return CrisisState(
            day=0,
            phase=CrisisPhase.BREAKOUT,
            approval_scores=approval,
            brand_values=brands,
            heat_index=round(initial_heat, 1),
            trending_topics=[],
            media_headlines=[],
            rumor_count=0,
            rumors=[],
            public_sentiment={"positive": 0.1, "negative": 0.6, "neutral": 0.3},
            regulatory_level=0,
            agent_actions=[],
            active_interventions=[],
            person_brands=person_brands,
        )

    async def step(self) -> CrisisState:
        """推进一天"""
        if self._finished:
            return self.current_state

        # 1. 推进时间
        phase = self.timeline.advance_day()
        day = self.timeline.current_day

        # 2. 检查干预
        state_dict = self.current_state.to_dict()
        triggered = self.intervention_system.check_interventions(day, state_dict)
        interventions_applied = []
        for cond in triggered:
            effects = self.intervention_system.apply_intervention(cond, self)
            interventions_applied.append({
                "day": day,
                "description": cond.description,
                "effects": effects,
            })

        # 3. 顺序决策：后决策的 Agent 看到前面人的动作 + 观众反应
        forced_actions: dict[str, PRAction] = {}
        for cond in triggered:
            if cond.person and cond.action:
                try:
                    forced_actions[cond.person] = PRAction(cond.action)
                except ValueError:
                    pass

        # 每日清空消息总线
        self.message_bus.clear()

        day_actions: list[CrisisAction] = []
        interaction_log: list[dict] = []
        is_free_mode = bool = (
            self.scenario.interaction_mode == InteractionMode.FREE
        )

        for name, agent in self.agents.items():
            forced = forced_actions.get(name)

            peer_actions = list(day_actions)

            # 观众对今天已有动作的反应
            audience_reactions: list[AgentMessage] = []
            if peer_actions:
                audience_reactions = await self.audience_pool.generate_reactions(
                    day, peer_actions, state_dict,
                )

            # 根据 interaction_mode 分支决策
            if is_free_mode:
                action = await agent.generate_free_response(
                    state_dict,
                    peer_actions=peer_actions,
                    audience_reactions=audience_reactions,
                )
            else:
                action = await agent.generate_crisis_response(
                    phase, state_dict,
                    forced_action=forced,
                    peer_actions=peer_actions,
                    audience_reactions=audience_reactions,
                )

            action.day = day
            day_actions.append(action)

            # 记录交互关系
            if action.triggered_by:
                trigger_action_label = next(
                    (a.action.label for a in day_actions
                     if a.actor == action.triggered_by),
                    "",
                )
                interaction_log.append({
                    "trigger": action.triggered_by,
                    "trigger_action": trigger_action_label,
                    "responder": name,
                    "response_action": action.action.label,
                    "relation": action.trigger_relation,
                })

            # 传播效应：检查是否有人需要对这条动作做出反应
            self._check_propagation(action)

        # 收集观众反应摘要
        all_audience_reactions = self.message_bus.get_audience_reactions()
        audience_summary = [
            {"sender": r.sender, "content": r.content, "sentiment": r.sentiment}
            for r in all_audience_reactions[:20]
        ]

        # 4. 信息真空检测 → 谣言
        new_rumors = self.vacuum_detector.update(
            day=day,
            day_actions=day_actions,
            involved_persons=self.scenario.involved_persons,
            gossip_type=self.scenario.gossip_type.value,
        )

        # 5. 计算动作效果
        for action in day_actions:
            effect = self.action_space.compute_effect(
                action=action.action,
                phase=phase,
                base_approval=self.current_state.approval_scores.get(action.actor, 50),
                personality=self.agents[action.actor].personality if action.actor in self.agents else None,
            )
            action.effects = effect
            action.day = day

            # 应用效果
            if action.actor in self.current_state.approval_scores:
                self.current_state.approval_scores[action.actor] = max(
                    0, min(100,
                        self.current_state.approval_scores[action.actor]
                        + effect["approval_delta"]
                    )
                )
            if action.actor in self.current_state.brand_values:
                self.current_state.brand_values[action.actor] = max(
                    0, min(100,
                        self.current_state.brand_values[action.actor]
                        + effect["brand_delta"]
                    )
                )
            # 热度
            self.current_state.heat_index = max(
                0, min(100,
                    self.current_state.heat_index + effect["heat_delta"]
                )
            )

        # 6. 谣言效果
        for rumor in new_rumors:
            person = rumor["person"]
            impact = self.vacuum_detector.get_rumor_impact(rumor)
            if person in self.current_state.approval_scores:
                self.current_state.approval_scores[person] = max(
                    0, self.current_state.approval_scores[person]
                    + impact["approval_delta"]
                )
            self.current_state.heat_index = min(
                100, self.current_state.heat_index + impact["heat_delta"]
            )
            self.current_state.rumor_count += 1

        # 7. 生成热搜和媒体
        trending = self._generate_trending(phase, day_actions)
        headlines = self._generate_headlines(phase, day_actions)

        # 8. 自然衰减
        self._apply_daily_decay()

        # 9. 品牌状态更新
        self._update_brands()

        # 10. 更新舆情分布
        self._update_sentiment()

        # 11. 监管升级
        self._check_regulatory(phase)

        # 构建新状态快照
        new_state = CrisisState(
            day=day,
            phase=phase,
            approval_scores=dict(self.current_state.approval_scores),
            brand_values=dict(self.current_state.brand_values),
            heat_index=self.current_state.heat_index,
            trending_topics=trending,
            media_headlines=headlines,
            rumor_count=self.current_state.rumor_count,
            rumors=list(self.current_state.rumors) + new_rumors,
            public_sentiment=dict(self.current_state.public_sentiment),
            regulatory_level=self.current_state.regulatory_level,
            agent_actions=day_actions,
            active_interventions=interventions_applied,
            person_brands={
                p: list(brands) for p, brands in self.current_state.person_brands.items()
            },
            audience_reactions=audience_summary,
            interaction_log=interaction_log,
        )

        self.current_state = new_state
        self.state_history.append(new_state)

        if self.timeline.is_finished():
            self._finished = True

        return new_state

    def _generate_trending(
        self, phase: CrisisPhase, actions: list[CrisisAction]
    ) -> list[TrendingTopic]:
        """生成热搜话题"""
        templates = TRENDING_TEMPLATES.get(phase, TRENDING_TEMPLATES[CrisisPhase.BREAKOUT])
        topics = []

        for i, name in enumerate(self.scenario.involved_persons[:5]):
            template = random.choice(templates)
            title = template.format(
                person=name,
                action=(
                    actions[0].free_action.label if actions[0].free_action
                    else actions[0].action.label
                ) if actions else "事件",
            )
            heat = max(10, self.current_state.heat_index - i * 15 + random.uniform(-10, 10))
            topics.append(TrendingTopic(
                rank=i + 1,
                title=title,
                heat=round(heat, 0),
                category="娱乐",
            ))

        # 按热度排序
        topics.sort(key=lambda t: t.heat, reverse=True)
        for i, t in enumerate(topics):
            t.rank = i + 1

        return topics

    def _generate_headlines(
        self, phase: CrisisPhase, actions: list[CrisisAction]
    ) -> list[MediaHeadline]:
        """生成媒体头条"""
        templates = MEDIA_TEMPLATES.get(phase, MEDIA_TEMPLATES[CrisisPhase.BREAKOUT])
        headlines = []

        for outlet, template in random.sample(templates, min(len(templates), 3)):
            person = random.choice(self.scenario.involved_persons)
            action_text = actions[0].action.label if actions else "事件发酵"
            headline = template.format(person=person, action=action_text)
            headlines.append(MediaHeadline(
                outlet=outlet,
                headline=headline,
                sentiment="negative" if phase in (
                    CrisisPhase.BREAKOUT, CrisisPhase.ESCALATION, CrisisPhase.PEAK
                ) else "neutral",
                reach=random.uniform(0.3, 1.0),
            ))

        return headlines

    def _apply_daily_decay(self) -> None:
        """每日自然衰减"""
        # 热度自然下降 10%
        self.current_state.heat_index = max(
            0, self.current_state.heat_index * 0.9
        )

        # 口碑向 50 回归
        for name in self.current_state.approval_scores:
            score = self.current_state.approval_scores[name]
            if score < 50:
                self.current_state.approval_scores[name] = min(
                    50, score + 0.5
                )
            elif score > 50:
                self.current_state.approval_scores[name] = max(
                    50, score - 0.3
                )

        # 品牌价值向 50 回归
        for name in self.current_state.brand_values:
            val = self.current_state.brand_values[name]
            if val < 50:
                self.current_state.brand_values[name] = min(50, val + 0.3)
            elif val > 50:
                self.current_state.brand_values[name] = max(50, val - 0.2)

    def _update_brands(self) -> None:
        """更新品牌状态"""
        for person, brand_list in self.current_state.person_brands.items():
            approval = self.current_state.approval_scores.get(person, 50)
            for brand in brand_list:
                brand.value = self.current_state.brand_values.get(person, 50)
                if approval < 20:
                    brand.action = "terminated"
                elif approval < 35:
                    brand.action = "suspended"
                elif approval < 50:
                    brand.action = "monitoring"
                else:
                    brand.action = "continue"

    def _update_sentiment(self) -> None:
        """更新舆情分布"""
        avg_approval = sum(self.current_state.approval_scores.values()) / max(
            1, len(self.current_state.approval_scores)
        )
        self.current_state.public_sentiment = {
            "positive": round(max(0.05, min(0.6, avg_approval / 100)), 2),
            "negative": round(max(0.05, min(0.8, 1 - avg_approval / 100)), 2),
            "neutral": round(max(0.1, 0.4 - abs(avg_approval - 50) / 200), 2),
        }

    def _check_regulatory(self, phase: CrisisPhase) -> None:
        """检查监管升级"""
        heat = self.current_state.heat_index
        level = self.current_state.regulatory_level

        if heat > 80 and level < 4:
            level += 1
        elif heat > 60 and level < 2:
            if random.random() < 0.3:
                level += 1
        elif heat < 30 and level > 0:
            level -= 1

        self.current_state.regulatory_level = max(0, min(5, level))

    def _check_propagation(self, action: CrisisAction) -> None:
        """检查一条动作是否会触发其他 Agent 的额外响应"""
        for name, agent in self.agents.items():
            if name == action.actor:
                continue
            rels = self.kg.get_relationship_context(name, action.actor)
            if not rels:
                continue
            relation_type = rels[0].get("relation_type", "")

            # 配偶/家人做了重大动作 → 标记需要回应
            if relation_type in ("配偶", "前配偶", "伴侣", "家人", "亲属") and \
               action.action in (
                   PRAction.APOLOGIZE, PRAction.COUNTERATTACK,
                   PRAction.PLAY_VICTIM, PRAction.STATEMENT,
               ):
                agent.memory.append(
                    f"PROPAGATION: {action.actor}做了{action.action.label}，我被触发回应"
                )

            # 对手做了攻击性动作 → 标记需要回应
            if relation_type in ("对手", "竞争对手", "宿敌", "同代竞争") and \
               action.action in (PRAction.COUNTERATTACK, PRAction.PLAY_VICTIM):
                agent.memory.append(
                    f"PROPAGATION: 对手{action.actor}做了{action.action.label}，我被触发回应"
                )

    async def run(self, days: int | None = None) -> list[CrisisState]:
        """运行仿真到底"""
        target = days or self.timeline.total_days
        while not self._finished and self.timeline.current_day < target:
            await self.step()
        return self.state_history

    def get_state(self) -> CrisisState:
        return self.current_state

    def get_history(self) -> list[dict]:
        return [s.to_dict() for s in self.state_history]

    def is_finished(self) -> bool:
        return self._finished

    def reset(self) -> None:
        self.timeline = CrisisTimeline(
            self.scenario.crisis_date or "2024-01-01",
            total_days=self.timeline.total_days,
        )
        self.state_history.clear()
        self.current_state = self._init_state()
        self.vacuum_detector.reset()
        self.intervention_system.reset()
        self.message_bus.clear()
        for agent in self.agents.values():
            agent.reset()
        self._finished = False

    def _estimate_base_approval(self, name: str) -> float:
        """从图谱数据推算基础口碑（危机前的公众形象）

        综合考量：粉丝量、作品数、过往负面事件数量、职业类型
        返回 20-95 的口碑分
        """
        node_id = f"celebrity:{name}"
        if not self.kg._graph.has_node(node_id):
            return 60.0

        data = self.kg._graph.nodes[node_id]

        # 1. 粉丝量贡献 (0-30)
        fans = data.get("weibo_followers", 0) or 0
        if fans >= 1e8:
            fans_score = 30
        elif fans >= 5e7:
            fans_score = 20 + min(10, (fans - 5e7) / 5e7 * 10)
        elif fans >= 1e6:
            fans_score = 12 + min(8, (fans - 1e6) / 4e7 * 8)
        elif fans >= 1e4:
            fans_score = 5 + min(7, (fans - 1e4) / 1e6 * 7)
        else:
            fans_score = 5

        # 2. 作品数贡献 (0-15)
        works = data.get("famous_works", []) or []
        works_score = min(15, len(works) * 2.5)

        # 3. 过往负面事件扣分 (0-20)
        events = self.kg.get_related_events(name)
        negative_events = [e for e in events if e.get("sentiment") == "negative"]
        event_penalty = min(20, len(negative_events) * 5)

        # 4. 职业加成 (0-10)
        occupation = data.get("occupation", [])
        occ_text = " ".join(str(o) for o in occupation)
        occ_bonus = 0
        if any(kw in occ_text for kw in ["演员", "歌手", "导演", "制片", "说唱"]):
            occ_bonus = 8
        elif any(kw in occ_text for kw in ["主持人", "模特", "偶像", "idol"]):
            occ_bonus = 5
        elif any(kw in occ_text for kw in ["舞者", "音乐人", "rapper", "DJ"]):
            occ_bonus = 3

        base = 50 + fans_score + works_score - event_penalty + occ_bonus
        return max(20, min(95, base))

