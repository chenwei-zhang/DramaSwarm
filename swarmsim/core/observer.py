"""
Observer Module - 观测总结模块

监控系统中的所有 Agent，分析群体动态并生成推演报告。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class ObservationType(Enum):
    """观测类型"""
    AGENT_STATE = "agent_state"
    INTERACTION = "interaction"
    CONFLICT = "conflict"
    ALLIANCE = "alliance"
    MOOD_SHIFT = "mood_shift"
    TENSION_SPIKE = "tension_spike"


@dataclass
class Observation:
    """单条观测记录"""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    type: ObservationType = ObservationType.INTERACTION
    description: str = ""
    participants: list[str] = field(default_factory=list)
    importance: float = 0.5
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "description": self.description,
            "participants": self.participants,
            "importance": self.importance,
            "metadata": self.metadata
        }


@dataclass
class AgentSnapshot:
    """Agent 状态快照"""
    agent_id: str
    agent_name: str
    timestamp: datetime
    state: str
    stress_level: float
    energy_level: float
    memory_count: int
    recent_actions: list[str]

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "stress_level": self.stress_level,
            "energy_level": self.energy_level,
            "memory_count": self.memory_count,
            "recent_actions": self.recent_actions
        }


class GroupMetrics:
    """群体指标"""

    def __init__(self):
        self.harmony_score = 0.5  # 和谐度 0-1
        self.activity_level = 0.5  # 活跃度 0-1
        self.diversity_score = 0.5  # 多样性 0-1
        self.conflict_count = 0
        self.alliance_count = 0

    def update(self, observations: list[Observation]) -> None:
        """根据观测更新指标"""
        conflict_obs = [o for o in observations if o.type == ObservationType.CONFLICT]
        alliance_obs = [o for o in observations if o.type == ObservationType.ALLIANCE]

        self.conflict_count = len(conflict_obs)
        self.alliance_count = len(alliance_obs)

        # 简化的和谐度计算
        if observations:
            avg_importance = sum(o.importance for o in observations) / len(observations)
            self.harmony_score = max(0, 1 - (self.conflict_count * 0.2 + avg_importance * 0.3))

    def to_dict(self) -> dict:
        return {
            "harmony_score": self.harmony_score,
            "activity_level": self.activity_level,
            "diversity_score": self.diversity_score,
            "conflict_count": self.conflict_count,
            "alliance_count": self.alliance_count
        }


class Observer:
    """
    观测者 Agent

    监控系统中的所有 Agent，记录重要事件，分析群体动态。
    类似于"上帝视角"的观察者。
    """

    def __init__(self, name: str = "Observer"):
        self.name = name
        self.observations: list[Observation] = []
        self.agent_snapshots: list[AgentSnapshot] = []
        self.metrics = GroupMetrics()

        # 回调
        self.on_critical_event: callable | None = None

        # 阈值配置
        self.critical_tension_threshold = 0.7
        self.critical_stress_threshold = 0.8

    def observe_action(self, action: dict) -> None:
        """观测一个行动"""
        action_type = action.get("action_type", "unknown")
        agent_name = action.get("agent_name", "Unknown")
        agent_id = action.get("agent_id", "")
        content = action.get("content", "")

        # 判断是否为重要观测
        importance = 0.5
        obs_type = ObservationType.INTERACTION

        if action_type == "speak":
            # 分析发言内容
            if any(word in content for word in ["!", "？", "?", "无法", "不能", "太"]):
                importance = 0.6

            if any(word in content for word in ["吵架", "矛盾", "问题", "不对"]):
                obs_type = ObservationType.CONFLICT
                importance = 0.8

        elif action_type == "conflict":
            obs_type = ObservationType.CONFLICT
            importance = 0.9

        # 使用 agent_name 作为参与者标识，方便显示
        observation = Observation(
            type=obs_type,
            description=f"{agent_name} {action_type}: {content[:50]}",
            participants=[agent_name or agent_id],
            importance=importance,
            metadata={"agent_id": agent_id}  # 保存 ID 以便查找
        )

        self.add_observation(observation)

    def observe_agent(self, agent: Any) -> AgentSnapshot:
        """观测单个 Agent 的状态"""
        snapshot = AgentSnapshot(
            agent_id=agent.id,
            agent_name=agent.name,
            timestamp=datetime.now(),
            state=agent.state.value,
            stress_level=agent.stress_level,
            energy_level=agent.energy_level,
            memory_count=len(agent.memory.memories),
            recent_actions=[m.content for m in agent.memory.get_recent(3)]
        )

        self.agent_snapshots.append(snapshot)

        # 检查临界状态
        if agent.stress_level > self.critical_stress_threshold:
            self.add_observation(Observation(
                type=ObservationType.TENSION_SPIKE,
                description=f"{agent.name} 压力过高: {agent.stress_level:.2f}",
                participants=[agent.id],
                importance=0.8
            ))

        return snapshot

    def observe_environment(self, environment: Any) -> None:
        """观测环境状态"""
        state = environment.state if hasattr(environment, "state") else environment

        if hasattr(state, "tension_level") and state.tension_level > self.critical_tension_threshold:
            self.add_observation(Observation(
                type=ObservationType.TENSION_SPIKE,
                description=f"环境紧张程度过高: {state.tension_level:.2f}",
                importance=0.9
            ))

    def observe_turn(self, turn_result: Any) -> None:
        """观测一个回合的结果"""
        for action in turn_result.actions:
            self.observe_action(action.to_dict())

        # 更新群体指标
        recent_obs = self.get_recent_observations(10)
        self.metrics.update(recent_obs)

    def add_observation(self, observation: Observation) -> None:
        """添加观测记录"""
        self.observations.append(observation)

        # 触发关键事件回调
        if observation.importance > 0.8 and self.on_critical_event:
            self.on_critical_event(observation)

    def get_recent_observations(self, n: int = 10) -> list[Observation]:
        """获取最近的观测"""
        return self.observations[-n:]

    def get_observations_by_type(
        self,
        obs_type: ObservationType
    ) -> list[Observation]:
        """按类型获取观测"""
        return [o for o in self.observations if o.type == obs_type]

    def get_observations_by_agent(self, agent_id: str) -> list[Observation]:
        """获取与特定 Agent 相关的观测"""
        return [
            o for o in self.observations
            if agent_id in o.participants
        ]

    def get_agent_timeline(self, agent_id: str) -> list[dict]:
        """获取 Agent 的时间线"""
        agent_snapshots = [
            s for s in self.agent_snapshots
            if s.agent_id == agent_id
        ]

        observations = self.get_observations_by_agent(agent_id)

        return {
            "snapshots": [s.to_dict() for s in agent_snapshots[-10:]],
            "observations": [o.to_dict() for o in observations[-10:]]
        }

    def analyze_group_dynamics(self) -> dict:
        """分析群体动态"""
        recent_obs = self.get_recent_observations(50)

        # 统计参与度
        participation: dict[str, int] = {}
        for obs in recent_obs:
            for participant in obs.participants:
                participation[participant] = participation.get(participant, 0) + 1

        # 统计冲突
        conflicts = self.get_observations_by_type(ObservationType.CONFLICT)
        conflict_pairs: dict[tuple[str, str], int] = {}
        for conflict in conflicts:
            if len(conflict.participants) >= 2:
                pair = tuple(sorted(conflict.participants[:2]))
                conflict_pairs[pair] = conflict_pairs.get(pair, 0) + 1

        return {
            "participation_ranking": sorted(
                participation.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            "conflict_hotspots": [
                {"pair": list(pair), "count": count}
                for pair, count in sorted(
                    conflict_pairs.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            ],
            "metrics": self.metrics.to_dict()
        }

    def generate_report(self) -> str:
        """生成观测报告"""
        dynamics = self.analyze_group_dynamics()

        report = f"""
=== 观测报告 ===
观测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 群体状态 ===
和谐度: {self.metrics.harmony_score:.2f}
活跃度: {self.metrics.activity_level:.2f}
冲突次数: {self.metrics.conflict_count}
联盟次数: {self.metrics.alliance_count}

=== 参与度排名 ===
"""

        for agent_id, count in dynamics["participation_ranking"][:5]:
            report += f"  {agent_id}: {count} 次参与\n"

        report += "\n=== 关键事件 ===\n"
        critical_events = [o for o in self.observations if o.importance > 0.7][-5:]
        for event in critical_events:
            report += f"  [{event.type.value}] {event.description}\n"

        return report

    def reset(self) -> None:
        """重置观测者"""
        self.observations = []
        self.agent_snapshots = []
        self.metrics = GroupMetrics()


class Reporter:
    """
    报告生成器

    基于观测数据生成各种格式的报告。
    """

    def __init__(self, observer: Observer):
        self.observer = observer

    def generate_summary(self) -> str:
        """生成摘要报告"""
        return self.observer.generate_report()

    def generate_detailed_report(self) -> dict:
        """生成详细报告"""
        dynamics = self.observer.analyze_group_dynamics()

        return {
            "summary": self.observer.generate_report(),
            "group_dynamics": dynamics,
            "recent_observations": [
                o.to_dict() for o in self.observer.get_recent_observations(20)
            ],
            "agent_snapshots": [
                s.to_dict() for s in self.observer.agent_snapshots[-20:]
            ],
            "metrics": dynamics["metrics"]
        }

    def generate_narrative(self) -> str:
        """生成叙事性报告（自然语言）"""
        dynamics = self.observer.analyze_group_dynamics()
        metrics = dynamics["metrics"]

        # 构建叙事
        narrative_parts = []

        # 整体氛围
        if metrics["harmony_score"] > 0.7:
            narrative_parts.append("整体氛围和谐融洽，成员间互动积极。")
        elif metrics["harmony_score"] > 0.4:
            narrative_parts.append("整体氛围平稳，但存在一些小摩擦。")
        else:
            narrative_parts.append("群体氛围紧张，冲突频繁。")

        # 冲突分析
        if metrics["conflict_count"] > 5:
            narrative_parts.append(
                f"观测期间发生了 {metrics['conflict_count']} 次冲突，"
                "主要集中在特定成员之间。"
            )

        # 最活跃的成员
        if dynamics["participation_ranking"]:
            top_agent, count = dynamics["participation_ranking"][0]
            narrative_parts.append(
                f"{top_agent} 是最活跃的参与者，"
                f"共参与了 {count} 次互动。"
            )

        return "\n\n".join(narrative_parts)

    def export_json(self) -> str:
        """导出 JSON 格式报告"""
        import json
        return json.dumps(
            self.generate_detailed_report(),
            ensure_ascii=False,
            indent=2
        )


class InteractiveObserver(Observer):
    """
    交互式观测者

    可以在仿真过程中主动干预和提问。
    """

    def __init__(self, name: str = "InteractiveObserver"):
        super().__init__(name)
        self.pending_questions: list[dict] = []

    def ask_agent(self, agent_id: str, question: str) -> dict:
        """向特定 Agent 提问"""
        self.pending_questions.append({
            "agent_id": agent_id,
            "question": question,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "status": "question_queued",
            "agent_id": agent_id,
            "question": question
        }

    def inject_intervention(
        self,
        event_type: str,
        description: str,
        severity: float = 0.5
    ) -> Observation:
        """注入外部干预"""
        observation = Observation(
            type=ObservationType.MOOD_SHIFT,
            description=f"[外部干预] {description}",
            importance=severity
        )

        self.add_observation(observation)
        return observation


async def observe_loop(
    observer: Observer,
    event_loop: Any,
    interval: float = 1.0
) -> None:
    """
    异步观测循环

    持续监控事件循环并记录观测。

    Args:
        observer: 观测者实例
        event_loop: 事件循环实例
        interval: 观测间隔（秒）
    """
    while event_loop.is_running:
        # 观测环境
        observer.observe_environment(event_loop.environment)

        # 观测所有 Agent
        for agent in event_loop.get_agents():
            observer.observe_agent(agent)

        await asyncio.sleep(interval)


def create_observer(
    observer_type: str = "default",
    **kwargs
) -> Observer:
    """
    便捷函数：创建观测者

    Args:
        observer_type: 观测者类型 (default, interactive)
        **kwargs: 其他配置参数

    Returns:
        Observer 实例
    """
    if observer_type == "interactive":
        return InteractiveObserver(**kwargs)
    return Observer(**kwargs)
