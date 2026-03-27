"""
Event Loop Module - 事件驱动引擎

控制 Agent 交互的节拍和状态流转，实现仿真世界的"心跳"。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class TurnPhase(Enum):
    """回合阶段"""
    PREPARATION = "preparation"  # 准备阶段
    PERCEPTION = "perception"    # 感知阶段
    DECISION = "decision"        # 决策阶段
    ACTION = "action"            # 行动阶段
    REFLECTION = "reflection"    # 反思阶段
    CLEANUP = "cleanup"          # 清理阶段


@dataclass
class TurnAction:
    """回合行动记录"""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    agent_name: str = ""
    action_type: str = "wait"  # speak, act, listen, wait
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    target_agents: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "target_agents": self.target_agents,
            "metadata": self.metadata
        }


@dataclass
class TurnResult:
    """回合结果"""
    turn_number: int
    phase: TurnPhase
    actions: list[TurnAction] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "turn_number": self.turn_number,
            "phase": self.phase.value,
            "actions": [a.to_dict() for a in self.actions],
            "events": self.events,
            "metadata": self.metadata
        }


class EventLoopConfig:
    """事件循环配置"""

    def __init__(
        self,
        tick_interval: float = 1.0,
        max_turns: int = 100,
        agents_per_turn: int = 3,  # 每回合允许行动的 Agent 数量
        phase_timeout: float = 30.0,  # 每阶段超时时间
        enable_parallel: bool = True,  # 是否启用并行处理
    ):
        self.tick_interval = tick_interval
        self.max_turns = max_turns
        self.agents_per_turn = agents_per_turn
        self.phase_timeout = phase_timeout
        self.enable_parallel = enable_parallel


class EventLoop:
    """
    事件驱动引擎

    管理仿真世界的回合制推进，控制 Agent 的行动顺序和交互流程。
    """

    def __init__(
        self,
        environment: Any,
        config: EventLoopConfig | None = None
    ):
        self.environment = environment
        self.config = config or EventLoopConfig()

        # 状态
        self.current_turn = 0
        self.current_phase = TurnPhase.PREPARATION
        self.is_running = False
        self.is_paused = False

        # 历史记录
        self.turn_history: list[TurnResult] = []
        self.action_history: list[TurnAction] = []

        # 回调
        self.on_turn_start: Callable | None = None
        self.on_turn_end: Callable | None = None
        self.on_phase_change: Callable | None = None
        self.on_action: Callable | None = None

        # 防复读机制
        self._recent_contents: list[str] = []
        self._max_recent_contents = 10

    def _is_repetitive(self, content: str, threshold: float = 0.7) -> bool:
        """检查内容是否重复"""
        content_lower = content.lower()
        for recent in self._recent_contents:
            if recent.lower() == content_lower:
                return True
            # 简单的相似度检查
            words_recent = set(recent.lower().split())
            words_content = set(content.lower().split())
            if words_recent and words_content:
                overlap = len(words_recent & words_content) / max(len(words_recent), len(words_content))
                if overlap > threshold:
                    return True
        return False

    def _record_content(self, content: str) -> None:
        """记录内容"""
        self._recent_contents.append(content)
        if len(self._recent_contents) > self._max_recent_contents:
            self._recent_contents.pop(0)

    def add_agent(self, agent: Any) -> None:
        """添加 Agent 到循环"""
        self.environment.register_agent(agent.id, agent)

    def remove_agent(self, agent_id: str) -> None:
        """从循环中移除 Agent"""
        self.environment.unregister_agent(agent_id)

    def get_agents(self) -> list[Any]:
        """获取所有 Agent"""
        return list(self.environment.agents.values())

    async def run(self, max_turns: int | None = None) -> list[TurnResult]:
        """
        运行事件循环

        Args:
            max_turns: 最大回合数，None 则使用配置值

        Returns:
            所有回合的结果列表
        """
        self.is_running = True
        max_turns = max_turns or self.config.max_turns

        try:
            while self.is_running and self.current_turn < max_turns:
                await self._wait_if_paused()
                result = await self._run_turn()
                self.turn_history.append(result)

                # 回合间延迟
                if self.current_turn < max_turns - 1:
                    await asyncio.sleep(self.config.tick_interval)

        except Exception as e:
            self.environment.add_event(
                "error",
                f"事件循环错误: {e}",
                severity=0.9
            )
        finally:
            self.is_running = False

        return self.turn_history

    async def _wait_if_paused(self) -> None:
        """如果暂停则等待"""
        while self.is_paused:
            await asyncio.sleep(0.1)

    def pause(self) -> None:
        """暂停循环"""
        self.is_paused = True

    def resume(self) -> None:
        """恢复循环"""
        self.is_paused = False

    def stop(self) -> None:
        """停止循环"""
        self.is_running = False

    async def _run_turn(self) -> TurnResult:
        """运行一个完整回合"""
        self.current_turn += 1

        if self.on_turn_start:
            await self.on_turn_start(self.current_turn)

        result = TurnResult(
            turn_number=self.current_turn,
            phase=TurnPhase.PREPARATION
        )

        # 阶段 1: 准备阶段
        await self._run_phase(result, TurnPhase.PREPARATION, self._phase_preparation)

        # 阶段 2: 感知阶段
        await self._run_phase(result, TurnPhase.PERCEPTION, self._phase_perception)

        # 阶段 3: 决策阶段
        await self._run_phase(result, TurnPhase.DECISION, self._phase_decision)

        # 阶段 4: 行动阶段
        await self._run_phase(result, TurnPhase.ACTION, self._phase_action)

        # 阶段 5: 反思阶段
        await self._run_phase(result, TurnPhase.REFLECTION, self._phase_reflection)

        # 阶段 6: 清理阶段
        await self._run_phase(result, TurnPhase.CLEANUP, self._phase_cleanup)

        # 推进环境时间
        self.environment.advance_turn()

        if self.on_turn_end:
            await self.on_turn_end(self.current_turn, result)

        return result

    async def _run_phase(
        self,
        result: TurnResult,
        phase: TurnPhase,
        phase_func: Callable
    ) -> None:
        """运行一个阶段"""
        self.current_phase = phase
        result.phase = phase

        if self.on_phase_change:
            await self.on_phase_change(self.current_turn, phase)

        try:
            await asyncio.wait_for(
                phase_func(result),
                timeout=self.config.phase_timeout
            )
        except asyncio.TimeoutError:
            result.events.append({
                "type": "warning",
                "message": f"阶段 {phase.value} 超时"
            })

    async def _phase_preparation(self, result: TurnResult) -> None:
        """准备阶段：选择本回合行动的 Agent"""
        agents = self.get_agents()

        # 随机选择或按规则选择 Agent
        import random
        selected = random.sample(
            agents,
            min(len(agents), self.config.agents_per_turn)
        )

        result.metadata["active_agents"] = [a.id for a in selected]

        # 通知被选中的 Agent
        for agent in selected:
            if hasattr(agent, "perceive"):
                agent.perceive({
                    "type": "turn_start",
                    "content": f"第 {self.current_turn} 回合开始",
                    "source": "event_loop"
                })

    async def _phase_perception(self, result: TurnResult) -> None:
        """感知阶段：Agent 感知环境信息"""
        active_agent_ids = result.metadata.get("active_agents", [])

        # 收集环境信息
        env_events = self.environment.get_recent_events()
        broadcasts = self.environment.broadcasts[-5:] if self.environment.broadcasts else []

        context = {
            "turn": self.current_turn,
            "environment": self.environment.get_description(),
            "recent_events": [e.description for e in env_events],
            "broadcasts": broadcasts
        }

        # 让 Agent 感知
        for agent_id in active_agent_ids:
            agent = self.environment.agents.get(agent_id)
            if agent and hasattr(agent, "perceive"):
                agent.perceive({
                    "type": "context_update",
                    "content": context,
                    "source": "environment"
                })

    async def _phase_decision(self, result: TurnResult) -> None:
        """决策阶段：Agent 进行思考和决策"""
        active_agent_ids = result.metadata.get("active_agents", [])

        for agent_id in active_agent_ids:
            agent = self.environment.agents.get(agent_id)
            if agent and hasattr(agent, "think"):
                try:
                    thought = await agent.think({
                        "turn": self.current_turn,
                        "environment": self.environment
                    })
                    result.metadata[f"{agent_id}_thought"] = thought
                except Exception:
                    pass

    async def _phase_action(self, result: TurnResult) -> None:
        """行动阶段：Agent 执行行动"""
        active_agent_ids = result.metadata.get("active_agents", [])

        # 随机决定行动顺序
        import random
        random.shuffle(active_agent_ids)

        for agent_id in active_agent_ids:
            agent = self.environment.agents.get(agent_id)
            if not agent:
                continue

            # 决定行动类型
            import random
            action_roll = random.random()

            if action_roll < 0.6:  # 60% 发言
                action = await self._agent_speak(agent, result)
            elif action_roll < 0.8:  # 20% 执行行动
                action = await self._agent_act(agent, result)
            else:  # 20% 等待
                action = TurnAction(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    action_type="wait",
                    content=f"{agent.name} 选择观察..."
                )

            if action:
                result.actions.append(action)
                self.action_history.append(action)

                # 让其他 Agent 倾听
                if action.action_type == "speak":
                    await self._broadcast_speech(action, active_agent_ids)

                if self.on_action:
                    self.on_action(action)

    async def _agent_speak(self, agent: Any, result: TurnResult) -> TurnAction | None:
        """Agent 发言"""
        try:
            content = await agent.speak({
                "turn": self.current_turn,
                "environment": self.environment.get_description()
            })

            # 检查重复
            if self._is_repetitive(content):
                # 如果重复，给个提示
                content = f"[{agent.name} 似乎想说什么但没说出口]"

            self._record_content(content)

            return TurnAction(
                agent_id=agent.id,
                agent_name=agent.name,
                action_type="speak",
                content=content
            )
        except Exception:
            return None

    async def _agent_act(self, agent: Any, result: TurnResult) -> TurnAction | None:
        """Agent 执行行动"""
        try:
            action_data = await agent.act({
                "turn": self.current_turn,
                "environment": self.environment
            })

            return TurnAction(
                agent_id=agent.id,
                agent_name=agent.name,
                action_type=action_data.get("type", "action"),
                content=action_data.get("description", ""),
                metadata=action_data
            )
        except Exception:
            return None

    async def _broadcast_speech(self, action: TurnAction, exclude_ids: list[str]) -> None:
        """广播发言给其他 Agent"""
        for agent_id, agent in self.environment.agents.items():
            if agent_id == action.agent_id or agent_id not in exclude_ids:
                continue
            if hasattr(agent, "listen"):
                agent.listen(action.agent_id, action.content)

    async def _phase_reflection(self, result: TurnResult) -> None:
        """反思阶段：Agent 更新内部状态"""
        for agent in self.get_agents():
            if hasattr(agent, "memory"):
                agent.memory.advance_turn()

    async def _phase_cleanup(self, result: TurnResult) -> None:
        """清理阶段：清理过期数据"""
        # 限制历史记录大小
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-500:]

    def get_action_summary(self, last_n: int = 10) -> list[dict]:
        """获取最近的行动摘要"""
        recent = self.action_history[-last_n:]
        return [a.to_dict() for a in recent]

    def get_statistics(self) -> dict:
        """获取统计信息"""
        action_types = {}
        agent_actions = {}

        for action in self.action_history:
            action_types[action.action_type] = action_types.get(action.action_type, 0) + 1
            agent_actions[action.agent_name] = agent_actions.get(action.agent_name, 0) + 1

        return {
            "total_turns": self.current_turn,
            "total_actions": len(self.action_history),
            "action_types": action_types,
            "most_active_agent": max(agent_actions.items(), key=lambda x: x[1]) if agent_actions else None,
            "agent_action_counts": agent_actions
        }

    def reset(self) -> None:
        """重置事件循环"""
        self.current_turn = 0
        self.current_phase = TurnPhase.PREPARATION
        self.turn_history = []
        self.action_history = []
        self._recent_contents = []


class SequentialEventLoop(EventLoop):
    """
    顺序事件循环

    Agent 按顺序依次行动，适合对话密集的场景。
    """

    async def _phase_action(self, result: TurnResult) -> None:
        """行动阶段：依次行动"""
        active_agent_ids = result.metadata.get("active_agents", [])

        for agent_id in active_agent_ids:
            agent = self.environment.agents.get(agent_id)
            if not agent:
                continue

            # 每个 Agent 都发言
            action = await self._agent_speak(agent, result)

            if action:
                result.actions.append(action)
                self.action_history.append(action)

                # 让后面的 Agent 能听到前面的话
                await self._broadcast_speech(action, active_agent_ids)

                if self.on_action:
                    self.on_action(action)


class InteractiveEventLoop(EventLoop):
    """
    交互式事件循环

    允许外部干预和动态注入事件。
    """

    def __init__(self, environment: Any, config: EventLoopConfig | None = None):
        super().__init__(environment, config)
        self.pending_interventions: list[dict] = []

    def inject_event(self, event_type: str, content: str, severity: float = 0.5) -> None:
        """注入外部事件"""
        self.pending_interventions.append({
            "type": event_type,
            "content": content,
            "severity": severity
        })

    async def _phase_action(self, result: TurnResult) -> None:
        """行动阶段：处理注入事件"""
        # 处理注入的事件
        while self.pending_interventions:
            intervention = self.pending_interventions.pop(0)
            self.environment.add_event(
                intervention["type"],
                intervention["content"],
                intervention["severity"]
            )
            self.environment.broadcast(
                intervention["content"],
                source="intervention",
                importance=intervention["severity"]
            )

        # 正常行动流程
        await super()._phase_action(result)
