"""
Basic tests for SwarmSim core modules.
"""

import pytest
import asyncio

from swarmsim.core.agent import SimpleAgent, AgentRole, AgentState
from swarmsim.core.environment import Environment, VarietyShowEnvironment
from swarmsim.core.event_loop import EventLoop, TurnAction
from swarmsim.core.factory import AgentFactory, VarietyShowFactory
from swarmsim.core.observer import Observer, Observation, ObservationType


class TestAgent:
    """测试 Agent 基本功能"""

    def test_create_agent(self):
        """测试创建 Agent"""
        agent = SimpleAgent("测试用户", AgentRole.LEADER)
        assert agent.name == "测试用户"
        assert agent.role == AgentRole.LEADER
        assert agent.state == AgentState.IDLE

    def test_agent_memory(self):
        """测试 Agent 记忆"""
        agent = SimpleAgent("记忆测试", AgentRole.PEACEMAKER)

        # 添加记忆
        agent.memory.add("这是一条测试记忆", "test", importance=0.8)

        assert len(agent.memory.memories) == 1
        assert agent.memory.memories[0].content == "这是一条测试记忆"

    def test_agent_perceive(self):
        """测试 Agent 感知"""
        agent = SimpleAgent("感知测试", AgentRole.PERFECTIONIST)

        agent.perceive({
            "type": "test",
            "content": "测试事件",
            "source": "environment"
        })

        assert len(agent.memory.memories) > 0

    @pytest.mark.asyncio
    async def test_agent_speak(self):
        """测试 Agent 发言"""
        agent = SimpleAgent("发言测试", AgentRole.DRAMA_QUEEN)

        response = await agent.speak({"turn": 1})

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_agent_relationships(self):
        """测试 Agent 关系设置"""
        agent1 = SimpleAgent("用户1", AgentRole.LEADER)
        agent2 = SimpleAgent("用户2", AgentRole.SLACKER)

        agent1.set_relationship(agent2.id, "friendly")
        assert agent2.id in agent1.personality.relationships
        assert agent1.personality.relationships[agent2.id] == "friendly"

    def test_stress_and_energy(self):
        """测试压力和精力系统"""
        agent = SimpleAgent("压力测试", AgentRole.PERFECTIONIST)

        assert agent.stress_level == 0.0
        assert agent.energy_level == 1.0

        agent.update_stress(0.3)
        agent.update_energy(-0.2)

        assert agent.stress_level == 0.3
        assert agent.energy_level == 0.8


class TestEnvironment:
    """测试环境模块"""

    def test_create_environment(self):
        """测试创建环境"""
        env = Environment("测试世界")
        assert env.name == "测试世界"
        assert env.current_turn == 0

    def test_register_agent(self):
        """测试注册 Agent"""
        env = Environment()
        agent = SimpleAgent("注册测试", AgentRole.WILDCARD)

        env.register_agent(agent.id, agent)

        assert agent.id in env.agents
        assert env.get_agent_count() == 1

    def test_add_event(self):
        """测试添加事件"""
        env = Environment()
        event = env.add_event("test", "测试事件")

        assert event.type == "test"
        assert event.description == "测试事件"
        assert len(env.events) >= 1  # 原始事件 + 反应层产生的事件

    def test_broadcast(self):
        """测试广播"""
        env = Environment()
        agent = SimpleAgent("广播接收", AgentRole.PEACEMAKER)
        env.register_agent(agent.id, agent)

        env.broadcast("这是一条测试广播", source="system")

        assert len(env.broadcasts) > 0
        # 广播应该被 Agent 感知到
        assert len(agent.memory.memories) > 0

    def test_advance_turn(self):
        """测试推进回合"""
        env = Environment()
        assert env.current_turn == 0

        env.advance_turn()
        assert env.current_turn == 1


class TestVarietyShowEnvironment:
    """测试综艺节目环境"""

    def test_create_variety_show_env(self):
        """测试创建综艺环境"""
        env = VarietyShowEnvironment(initial_budget=500.0)

        assert env.budget == 500.0
        assert env.initial_budget == 500.0

    def test_set_task(self):
        """测试设置任务"""
        env = VarietyShowEnvironment()

        env.set_task("完成一个挑战", deadline_hours=12)

        assert env.current_task == "完成一个挑战"
        assert env.task_deadline is not None

    def test_consume_budget(self):
        """测试消耗预算"""
        env = VarietyShowEnvironment(initial_budget=100.0)

        success = env.consume_budget(30.0, "agent_1")
        assert success is True
        assert env.budget == 70.0

        # 尝试超支
        fail = env.consume_budget(100.0, "agent_1")
        assert fail is False

    def test_screen_time(self):
        """测试出镜时长"""
        env = VarietyShowEnvironment()

        env.record_screen_time("agent_1", 10)
        env.record_screen_time("agent_1", 5)
        env.record_screen_time("agent_2", 15)

        assert env.screen_time["agent_1"] == 15
        assert env.screen_time["agent_2"] == 15

        ranking = env.get_screen_time_ranking()
        assert len(ranking) == 2


class TestEventLoop:
    """测试事件循环"""

    def test_create_event_loop(self):
        """测试创建事件循环"""
        env = Environment()
        loop = EventLoop(env)

        assert loop.environment == env
        assert loop.current_turn == 0

    def test_add_remove_agent(self):
        """测试添加移除 Agent"""
        env = Environment()
        loop = EventLoop(env)
        agent = SimpleAgent("循环测试", AgentRole.LEADER)

        loop.add_agent(agent)
        assert agent.id in env.agents

        loop.remove_agent(agent.id)
        assert agent.id not in env.agents

    @pytest.mark.asyncio
    async def test_single_turn(self):
        """测试单回合运行"""
        env = Environment()
        loop = EventLoop(env)

        agent1 = SimpleAgent("Agent1", AgentRole.LEADER)
        agent2 = SimpleAgent("Agent2", AgentRole.PEACEMAKER)

        loop.add_agent(agent1)
        loop.add_agent(agent2)

        # 运行一回合
        result = await loop._run_turn()

        assert result.turn_number == 1
        assert len(result.actions) > 0


class TestAgentFactory:
    """测试 Agent 工厂"""

    def test_create_agent(self):
        """测试创建 Agent"""
        factory = AgentFactory()
        agent = factory.create("工厂测试", AgentRole.PERFECTIONIST)

        assert agent.name == "工厂测试"
        assert agent.role == AgentRole.PERFECTIONIST

    def test_create_from_dict(self):
        """测试从字典创建"""
        factory = AgentFactory()
        data = {
            "name": "字典测试",
            "role": "wildcard",
            "traits": ["creative", "unpredictable"]
        }

        agent = factory.create_from_dict(data)

        assert agent.name == "字典测试"
        assert agent.role == AgentRole.WILDCARD

    def test_create_batch(self):
        """测试批量创建"""
        factory = AgentFactory()
        configs = [
            {"name": "A", "role": "leader"},
            {"name": "B", "role": "peacemaker"},
            {"name": "C", "role": "drama_queen"}
        ]

        agents = factory.create_batch(configs, shuffle_names=False)

        assert len(agents) == 3
        assert agents[0].name == "A"


class TestVarietyShowFactory:
    """测试综艺工厂"""

    def test_create_cast(self):
        """测试创建综艺阵容"""
        factory = VarietyShowFactory()
        names = ["张三", "李四", "王五", "赵六"]

        agents = factory.create_cast("sisters_trip", names)

        assert len(agents) == 4
        assert all(isinstance(a, SimpleAgent) for a in agents)


class TestObserver:
    """测试观测者"""

    def test_create_observer(self):
        """测试创建观测者"""
        observer = Observer()

        assert len(observer.observations) == 0
        assert observer.metrics.conflict_count == 0

    def test_observe_action(self):
        """测试观测行动"""
        observer = Observer()

        action = TurnAction(
            agent_id="test_1",
            agent_name="测试",
            action_type="speak",
            content="这是一条发言"
        )

        observer.observe_action(action.to_dict())

        assert len(observer.observations) > 0

    def test_observe_agent(self):
        """测试观测 Agent"""
        observer = Observer()
        agent = SimpleAgent("被观测", AgentRole.SLACKER)

        snapshot = observer.observe_agent(agent)

        assert snapshot.agent_name == "被观测"
        assert len(observer.agent_snapshots) > 0

    def test_group_dynamics(self):
        """测试群体动态分析"""
        from swarmsim.core.observer import Observation
        observer = Observer()

        # 添加一些观测
        observer.add_observation(Observation(
            type=ObservationType.CONFLICT,
            description="测试冲突",
            participants=["a", "b"],
            importance=0.8
        ))

        dynamics = observer.analyze_group_dynamics()

        assert "participation_ranking" in dynamics
        assert "metrics" in dynamics
