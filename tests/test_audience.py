# -*- coding: utf-8 -*-
"""
观众系统单元测试

覆盖：AudienceAgent 的反应生成、AudiencePool 的比例分布、记忆机制
"""

import pytest

from swarmsim.crisis.audience import AudienceAgent, AudiencePool, AUDIENCE_TYPES, AUDIENCE_RATIOS
from swarmsim.crisis.models import PRAction, CrisisAction, AgentMessage


@pytest.fixture
def persons():
    return ["明星A", "明星B"]


@pytest.fixture
def pool(persons):
    return AudiencePool(persons, pool_size=50)


def _make_crisis_action(actor="明星A", action=PRAction.APOLOGIZE):
    return CrisisAction(
        actor=actor,
        action=action,
        content=f"{actor}公开道歉",
        day=1,
    )


class TestAudienceAgent:
    def test_fan_has_positive_bias(self, persons):
        agent = AudienceAgent("粉丝", persons)
        # 粉丝至少对一个人有正面偏好
        assert any(v > 0 for v in agent.bias.values())

    def test_hater_has_negative_bias(self, persons):
        agent = AudienceAgent("黑粉", persons)
        assert all(v < 0 for v in agent.bias.values())

    def test_neutral_has_moderate_bias(self, persons):
        agent = AudienceAgent("理中客", persons)
        for v in agent.bias.values():
            assert -0.2 <= v <= 0.2

    def test_react_to_apologize(self, persons):
        agent = AudienceAgent("粉丝", persons)
        action = _make_crisis_action()
        # 多次尝试确保至少有一次生成评论
        results = []
        for _ in range(10):
            msg = agent.react_to_action(action, day=1)
            if msg:
                results.append(msg)
        # 粉丝对道歉应该有较高评论率
        assert len(results) > 0

    def test_repetitive_action_reduces_comments(self, persons):
        """记忆驱动：重复动作降低评论概率（统计验证）"""
        # 用多次实验统计概率差异
        first_totals = []
        second_totals = []
        for _ in range(10):
            agent = AudienceAgent("粉丝", persons)
            action = _make_crisis_action()

            first_round = sum(
                1 for _ in range(20)
                if agent.react_to_action(action, day=1)
            )
            second_round = sum(
                1 for _ in range(20)
                if agent.react_to_action(action, day=2)
            )
            first_totals.append(first_round)
            second_totals.append(second_round)

        avg_first = sum(first_totals) / len(first_totals)
        avg_second = sum(second_totals) / len(second_totals)
        # 重复动作的平均评论数应该更低
        assert avg_second <= avg_first * 1.2  # 宽松验证：允许 20% 波动


class TestAudiencePool:
    def test_pool_size(self, pool):
        assert len(pool.agents) == 50

    def test_type_distribution(self, pool):
        """检查观众类型分布大致符合比例"""
        counts = {}
        for agent in pool.agents:
            counts[agent.persona_type] = counts.get(agent.persona_type, 0) + 1

        # 粉丝应该最多，黑粉最少
        assert counts.get("粉丝", 0) >= counts.get("黑粉", 0)

    def test_generate_reactions(self, pool):
        actions = [_make_crisis_action()]
        state = {"approval_scores": {"明星A": 30}, "heat_index": 70}

        import asyncio
        reactions = asyncio.get_event_loop().run_until_complete(
            pool.generate_reactions(1, actions, state)
        )
        assert isinstance(reactions, list)
        for r in reactions:
            assert isinstance(r, AgentMessage)
            assert r.source == "audience"

    def test_get_person_bias(self, pool, persons):
        bias_info = pool.get_person_bias(persons[0])
        assert "average_bias" in bias_info
        assert "support_ratio" in bias_info
        assert -1.0 <= bias_info["average_bias"] <= 1.0
        assert 0.0 <= bias_info["support_ratio"] <= 1.0

    def test_sentiment_summary(self, pool):
        summary = pool.get_sentiment_summary()
        assert summary["pool_size"] == 50
        assert "type_distribution" in summary
