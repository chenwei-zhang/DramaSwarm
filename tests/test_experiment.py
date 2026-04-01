# -*- coding: utf-8 -*-
"""测试 A/B 对照实验系统"""

import pytest

from swarmsim.graph.temporal import TemporalKnowledgeGraph
from swarmsim.crisis.experiment import (
    ExperimentManager,
    Experiment,
    ExperimentGroup,
    ExperimentGroupResult,
    ComparisonResult,
)


def _make_kg() -> TemporalKnowledgeGraph:
    """构建含基础明星的测试知识图谱"""
    kg = TemporalKnowledgeGraph()
    names = ["杨幂", "赵丽颖", "肖战", "王一博", "迪丽热巴", "李小璐", "贾乃亮", "PG One"]
    kg.load_from_mock_data(names)
    return kg


class TestExperimentManagerCreate:

    def setup_method(self):
        self.kg = _make_kg()
        self.mgr = ExperimentManager(self.kg)

    def test_create_returns_experiment(self):
        exp = self.mgr.create_experiment(
            scenario_title="测试场景",
            groups=[{"name": "对照组"}, {"name": "实验组"}],
        )
        assert isinstance(exp, Experiment)
        assert exp.experiment_id == "exp_1"
        assert exp.scenario_title == "测试场景"
        assert exp.status == "created"
        assert len(exp.groups) == 2

    def test_auto_increment_id(self):
        self.mgr.create_experiment(scenario_title="A", groups=[{"name": "G1"}])
        exp2 = self.mgr.create_experiment(scenario_title="B", groups=[{"name": "G2"}])
        assert exp2.experiment_id == "exp_2"

    def test_stored_in_experiments(self):
        exp = self.mgr.create_experiment(
            scenario_title="S", groups=[{"name": "G"}],
        )
        assert self.mgr.experiments["exp_1"] is exp

    def test_groups_default_name(self):
        exp = self.mgr.create_experiment(
            scenario_title="S", groups=[{}, {}],
        )
        assert exp.groups[0].name == "组1"
        assert exp.groups[1].name == "组2"

    def test_interventions_parsed(self):
        groups = [{
            "name": "道歉组",
            "interventions": [
                {"trigger_type": "time_absolute", "day": 3, "person": "杨幂", "action": "apologize"},
            ],
        }]
        exp = self.mgr.create_experiment(scenario_title="S", groups=groups)
        assert len(exp.groups[0].interventions) == 1
        iv = exp.groups[0].interventions[0]
        assert iv.day == 3
        assert iv.person == "杨幂"
        assert iv.action == "apologize"

    def test_use_llm_flag(self):
        exp = self.mgr.create_experiment(
            scenario_title="S", groups=[{"name": "G"}], use_llm=True,
        )
        assert exp.use_llm is True

    def test_total_days(self):
        exp = self.mgr.create_experiment(
            scenario_title="S", groups=[{"name": "G"}], total_days=15,
        )
        assert exp.total_days == 15


class TestExperimentManagerListAndGet:

    def setup_method(self):
        self.kg = _make_kg()
        self.mgr = ExperimentManager(self.kg)

    def test_list_experiments(self):
        self.mgr.create_experiment(scenario_title="A", groups=[{"name": "G"}])
        self.mgr.create_experiment(scenario_title="B", groups=[{"name": "G"}])
        result = self.mgr.list_experiments()
        assert len(result) == 2
        assert result[0]["scenario_title"] == "A"
        assert result[1]["scenario_title"] == "B"

    def test_get_experiment(self):
        exp = self.mgr.create_experiment(scenario_title="S", groups=[{"name": "G"}])
        found = self.mgr.get_experiment("exp_1")
        assert found is exp

    def test_get_nonexistent(self):
        assert self.mgr.get_experiment("exp_999") is None


class TestExperimentToDict:

    def test_basic_fields(self):
        kg = _make_kg()
        mgr = ExperimentManager(kg)
        exp = mgr.create_experiment(
            scenario_title="测试",
            groups=[{"name": "对照组"}, {"name": "道歉组", "interventions": [
                {"day": 3, "person": "杨幂", "action": "apologize"},
            ]}],
            total_days=20,
        )
        d = exp.to_dict()
        assert d["experiment_id"] == "exp_1"
        assert d["scenario_title"] == "测试"
        assert d["status"] == "created"
        assert d["total_days"] == 20
        assert len(d["groups"]) == 2
        assert d["groups"][0]["name"] == "对照组"
        assert d["groups"][1]["intervention_count"] == 1
        assert d["groups"][1]["interventions"][0]["person"] == "杨幂"

    def test_empty_results(self):
        kg = _make_kg()
        mgr = ExperimentManager(kg)
        exp = mgr.create_experiment(scenario_title="S", groups=[{"name": "G"}])
        d = exp.to_dict()
        assert d["results"] == []


class TestExperimentManagerCompare:

    def setup_method(self):
        self.kg = _make_kg()
        self.mgr = ExperimentManager(self.kg)

    def test_compare_not_found(self):
        with pytest.raises(ValueError, match="未找到实验"):
            self.mgr.compare_experiment("exp_999")

    def test_compare_not_completed(self):
        self.mgr.create_experiment(scenario_title="S", groups=[{"name": "G"}])
        with pytest.raises(ValueError, match="实验尚未完成"):
            self.mgr.compare_experiment("exp_1")

    def test_compare_basic(self):
        exp = self.mgr.create_experiment(
            scenario_title="S",
            groups=[{"name": "对照组"}, {"name": "道歉组"}],
        )
        exp.status = "completed"
        exp.results = [
            ExperimentGroupResult(
                group_name="对照组",
                final_state={"approval_scores": {"杨幂": 40, "肖战": 50}},
                total_days=30,
            ),
            ExperimentGroupResult(
                group_name="道歉组",
                final_state={"approval_scores": {"杨幂": 55, "肖战": 60}},
                total_days=30,
            ),
        ]
        result = self.mgr.compare_experiment("exp_1")
        assert isinstance(result, ComparisonResult)
        assert result.experiment_id == "exp_1"
        assert len(result.groups_summary) == 2
        assert result.best_group == "道歉组"

    def test_compare_per_person_delta(self):
        exp = self.mgr.create_experiment(
            scenario_title="S",
            groups=[{"name": "对照组"}, {"name": "道歉组"}],
        )
        exp.status = "completed"
        exp.results = [
            ExperimentGroupResult(
                group_name="对照组",
                final_state={"approval_scores": {"杨幂": 40}},
                total_days=30,
            ),
            ExperimentGroupResult(
                group_name="道歉组",
                final_state={"approval_scores": {"杨幂": 55}},
                total_days=30,
            ),
        ]
        result = self.mgr.compare_experiment("exp_1")
        assert "道歉组" in result.per_person_delta
        assert result.per_person_delta["道歉组"]["杨幂"] == 15.0

    def test_compare_with_empty_final_state(self):
        exp = self.mgr.create_experiment(
            scenario_title="S",
            groups=[{"name": "对照组"}, {"name": "实验组"}],
        )
        exp.status = "completed"
        exp.results = [
            ExperimentGroupResult(group_name="对照组", final_state=None, total_days=0),
            ExperimentGroupResult(
                group_name="实验组",
                final_state={"approval_scores": {"杨幂": 60}},
                total_days=30,
            ),
        ]
        result = self.mgr.compare_experiment("exp_1")
        assert result.groups_summary[0]["avg_approval"] == 0
        assert result.best_group == "实验组"

    def test_compare_recommendations(self):
        exp = self.mgr.create_experiment(
            scenario_title="S",
            groups=[{"name": "对照组"}, {"name": "道歉组"}],
        )
        exp.status = "completed"
        exp.results = [
            ExperimentGroupResult(
                group_name="对照组",
                final_state={"approval_scores": {"杨幂": 40, "肖战": 50}},
                total_days=30,
            ),
            ExperimentGroupResult(
                group_name="道歉组",
                final_state={"approval_scores": {"杨幂": 55, "肖战": 45}},
                total_days=30,
            ),
        ]
        result = self.mgr.compare_experiment("exp_1")
        assert len(result.recommendations) >= 1
        assert any("最佳干预策略" in r for r in result.recommendations)
        assert any("杨幂" in r and "口碑提升" in r for r in result.recommendations)
        assert any("肖战" in r and "口碑下降" in r for r in result.recommendations)

    def test_compare_single_group_no_delta(self):
        exp = self.mgr.create_experiment(
            scenario_title="S",
            groups=[{"name": "对照组"}],
        )
        exp.status = "completed"
        exp.results = [
            ExperimentGroupResult(
                group_name="对照组",
                final_state={"approval_scores": {"杨幂": 50}},
                total_days=30,
            ),
        ]
        result = self.mgr.compare_experiment("exp_1")
        assert result.per_person_delta == {}

    def test_compare_with_outcome_report(self):
        exp = self.mgr.create_experiment(
            scenario_title="S",
            groups=[{"name": "对照组"}],
        )
        exp.status = "completed"
        exp.results = [
            ExperimentGroupResult(
                group_name="对照组",
                final_state={"approval_scores": {"杨幂": 50}},
                total_days=30,
                outcome_report={"verdict": "similar", "verdict_label": "与历史相似"},
            ),
        ]
        result = self.mgr.compare_experiment("exp_1")
        assert result.groups_summary[0]["verdict"] == "similar"
        assert result.groups_summary[0]["verdict_label"] == "与历史相似"


class TestComparisonResultToDict:

    def test_to_dict(self):
        cr = ComparisonResult(
            experiment_id="exp_1",
            scenario_title="测试",
            best_group="道歉组",
            best_metric="平均口碑 55.0",
            groups_summary=[{"group_name": "道歉组", "avg_approval": 55}],
            per_person_delta={"道歉组": {"杨幂": 15}},
            recommendations=["最佳干预策略: 道歉组"],
        )
        d = cr.to_dict()
        assert d["experiment_id"] == "exp_1"
        assert d["best_group"] == "道歉组"
        assert d["per_person_delta"]["道歉组"]["杨幂"] == 15
        assert len(d["recommendations"]) == 1
