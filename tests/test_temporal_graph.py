# -*- coding: utf-8 -*-
"""测试时序知识图谱"""

import pytest
from swarmsim.graph.temporal import TemporalKnowledgeGraph


@pytest.fixture
def kg():
    """创建带数据的时序图谱"""
    graph = TemporalKnowledgeGraph()
    names = ["李小璐", "贾乃亮", "PG One"]
    graph.load_from_mock_data(names)
    return graph


class TestTemporalKnowledgeGraph:

    def test_load_creates_timeline_index(self, kg):
        """加载后应有时序索引"""
        assert len(kg._timeline_index) > 0

    def test_load_creates_person_timelines(self, kg):
        """加载后应有人物时间线"""
        for name in ["李小璐", "贾乃亮", "PG One"]:
            timeline = kg.get_person_timeline(name)
            assert isinstance(timeline, list)

    def test_get_events_on_date(self, kg):
        """按日期查询事件"""
        # 随便找一个存在的日期
        if kg._timeline_index:
            first_date = kg._timeline_index[0][0]
            events = kg.get_events_on_date(first_date)
            assert isinstance(events, list)

    def test_get_events_in_range(self, kg):
        """日期范围查询"""
        if kg._timeline_index:
            dates = [d for d, _ in kg._timeline_index]
            if len(dates) >= 2:
                events = kg.get_events_in_range(dates[0], dates[-1])
                assert isinstance(events, list)

    def test_get_person_events_in_range(self, kg):
        """人物日期范围事件"""
        name = "李小璐"
        timeline = kg.get_person_timeline(name)
        if timeline:
            first_date = timeline[0].get("date", "")
            if first_date:
                events = kg.get_person_events_in_range(name, first_date, "2099-12-31")
                assert isinstance(events, list)

    def test_get_all_timelines(self, kg):
        """获取所有时间线"""
        timelines = kg.get_all_timelines()
        assert isinstance(timelines, dict)

    def test_list_crisis_scenarios(self, kg):
        """列出危机场景"""
        scenarios = kg.list_crisis_scenarios(min_importance=0.3)
        assert isinstance(scenarios, list)
        for s in scenarios:
            assert "title" in s
            assert "importance" in s
            assert "involved_persons" in s

    def test_get_crisis_scenario_data(self, kg):
        """获取场景数据"""
        scenarios = kg.list_crisis_scenarios(min_importance=0.1)
        if scenarios:
            data = kg.get_crisis_scenario_data(scenarios[0]["title"])
            if data:
                assert "title" in data
                assert "involved_persons" in data

    def test_reset(self, kg):
        """重置图谱"""
        kg.reset()
        assert len(kg._timeline_index) == 0
        assert len(kg._person_timelines) == 0
        assert kg.node_count == 0
