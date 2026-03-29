# -*- coding: utf-8 -*-
"""
A/B 对照实验系统

支持同一场景多组不同干预配置的对比实验。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from swarmsim.crisis.models import (
    CrisisScenario, CrisisState, InterventionCondition, InteractionMode,
)


@dataclass
class ExperimentGroup:
    """实验组配置"""
    name: str                                      # 组名，如"对照组"、"道歉组"
    interventions: list[InterventionCondition] = field(default_factory=list)
    description: str = ""


@dataclass
class ExperimentGroupResult:
    """一组实验的运行结果"""
    group_name: str
    history: list[dict] = field(default_factory=list)
    final_state: dict | None = None
    outcome_report: dict | None = None
    total_days: int = 0


@dataclass
class Experiment:
    """一次完整实验"""
    experiment_id: str
    scenario_title: str
    groups: list[ExperimentGroup] = field(default_factory=list)
    results: list[ExperimentGroupResult] = field(default_factory=list)
    status: str = "created"          # created / running / completed
    use_llm: bool = False
    total_days: int = 30

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "scenario_title": self.scenario_title,
            "status": self.status,
            "use_llm": self.use_llm,
            "total_days": self.total_days,
            "groups": [
                {
                    "name": g.name,
                    "description": g.description,
                    "intervention_count": len(g.interventions),
                    "interventions": [
                        {
                            "day": iv.day,
                            "person": iv.person,
                            "action": iv.action,
                            "description": iv.description,
                            "trigger_type": iv.trigger_type,
                            "event_type": iv.event_type,
                        }
                        for iv in g.interventions
                    ],
                }
                for g in self.groups
            ],
            "results": [
                {
                    "group_name": r.group_name,
                    "total_days": r.total_days,
                    "final_state": r.final_state,
                }
                for r in self.results
            ],
        }


@dataclass
class ComparisonResult:
    """实验对比结果"""
    experiment_id: str
    scenario_title: str
    groups_summary: list[dict] = field(default_factory=list)
    best_group: str = ""             # 最佳策略组名
    best_metric: str = ""            # 评判指标
    per_person_delta: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "scenario_title": self.scenario_title,
            "best_group": self.best_group,
            "best_metric": self.best_metric,
            "groups_summary": self.groups_summary,
            "per_person_delta": self.per_person_delta,
            "recommendations": self.recommendations,
        }


class ExperimentManager:
    """实验管理器"""

    def __init__(self, kg):
        self.kg = kg
        self.experiments: dict[str, Experiment] = {}
        self._counter = 0

    def create_experiment(
        self,
        scenario_title: str,
        groups: list[dict],
        use_llm: bool = False,
        total_days: int = 30,
    ) -> Experiment:
        """创建实验

        Args:
            scenario_title: 场景标题
            groups: [{"name": "对照组", "description": "...", "interventions": [...]}]
            use_llm: 是否使用 LLM
            total_days: 仿真天数

        Returns:
            Experiment
        """
        self._counter += 1
        exp_id = f"exp_{self._counter}"

        exp_groups = []
        for g in groups:
            interventions = []
            for iv in g.get("interventions", []):
                interventions.append(InterventionCondition(
                    trigger_type=iv.get("trigger_type", "time_absolute"),
                    day=iv.get("day"),
                    person=iv.get("person"),
                    action=iv.get("action"),
                    description=iv.get("description", ""),
                    event_type=iv.get("event_type"),
                    external_event=iv.get("external_event"),
                    metric=iv.get("metric"),
                    threshold=iv.get("threshold"),
                    comparator=iv.get("comparator"),
                    person_a=iv.get("person_a"),
                    person_b=iv.get("person_b"),
                    relationship_change=iv.get("relationship_change"),
                ))
            exp_groups.append(ExperimentGroup(
                name=g.get("name", f"组{len(exp_groups)+1}"),
                interventions=interventions,
                description=g.get("description", ""),
            ))

        experiment = Experiment(
            experiment_id=exp_id,
            scenario_title=scenario_title,
            groups=exp_groups,
            use_llm=use_llm,
            total_days=total_days,
        )
        self.experiments[exp_id] = experiment
        return experiment

    async def run_experiment(self, experiment_id: str) -> Experiment:
        """运行实验（依次运行每组）"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"未找到实验: {experiment_id}")

        experiment.status = "running"
        experiment.results.clear()

        from swarmsim.crisis.scenario_engine import CrisisScenarioEngine
        engine = CrisisScenarioEngine(self.kg)

        for group in experiment.groups:
            try:
                sim = engine.create_simulation(
                    scenario_title=experiment.scenario_title,
                    use_llm=experiment.use_llm,
                    total_days=experiment.total_days,
                    interventions=group.interventions,
                )

                history = await sim.run()
                final_state = sim.get_state()

                # 生成结果报告
                outcome_report = None
                if sim.state_history:
                    from swarmsim.crisis.outcome_analyzer import OutcomeAnalyzer
                    analyzer = OutcomeAnalyzer()
                    report = analyzer.analyze(sim.state_history, sim.scenario)
                    outcome_report = report.to_dict()

                experiment.results.append(ExperimentGroupResult(
                    group_name=group.name,
                    history=[s.to_dict() for s in history],
                    final_state=final_state.to_dict(),
                    outcome_report=outcome_report,
                    total_days=len(history),
                ))
            except Exception as e:
                experiment.results.append(ExperimentGroupResult(
                    group_name=group.name,
                    total_days=0,
                ))

        experiment.status = "completed"
        return experiment

    def compare_experiment(self, experiment_id: str) -> ComparisonResult:
        """对比实验结果"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"未找到实验: {experiment_id}")

        if experiment.status != "completed":
            raise ValueError("实验尚未完成")

        result = ComparisonResult(
            experiment_id=experiment_id,
            scenario_title=experiment.scenario_title,
        )

        # 计算各组摘要
        for r in experiment.results:
            if not r.final_state:
                result.groups_summary.append({
                    "group_name": r.group_name,
                    "total_days": r.total_days,
                    "avg_approval": 0,
                    "min_approval": 0,
                })
                continue

            approvals = r.final_state.get("approval_scores", {})
            avg_approval = sum(approvals.values()) / max(1, len(approvals))
            min_approval = min(approvals.values()) if approvals else 0

            summary = {
                "group_name": r.group_name,
                "total_days": r.total_days,
                "avg_approval": round(avg_approval, 1),
                "min_approval": round(min_approval, 1),
                "final_approvals": approvals,
                "heat_index": r.final_state.get("heat_index", 0),
                "regulatory_level": r.final_state.get("regulatory_level", 0),
            }
            if r.outcome_report:
                summary["verdict"] = r.outcome_report.get("verdict", "")
                summary["verdict_label"] = r.outcome_report.get("verdict_label", "")
            result.groups_summary.append(summary)

        # 找出最佳组（按平均口碑）
        valid_groups = [s for s in result.groups_summary if s.get("avg_approval", 0) > 0]
        if valid_groups:
            best = max(valid_groups, key=lambda s: s.get("avg_approval", 0))
            result.best_group = best["group_name"]
            result.best_metric = f"平均口碑 {best.get('avg_approval', 0):.1f}"

        # 计算每人的口碑差值（相对于对照组）
        if len(experiment.results) >= 2:
            baseline = experiment.results[0]  # 第一组作为基线
            baseline_approvals = (
                baseline.final_state.get("approval_scores", {})
                if baseline.final_state else {}
            )
            for r in experiment.results[1:]:
                if not r.final_state:
                    continue
                approvals = r.final_state.get("approval_scores", {})
                deltas = {}
                for person in approvals:
                    base_val = baseline_approvals.get(person, 50)
                    deltas[person] = round(approvals[person] - base_val, 1)
                result.per_person_delta[r.group_name] = deltas

        # 生成建议
        if result.best_group:
            result.recommendations.append(
                f"最佳干预策略: {result.best_group}（{result.best_metric}）"
            )
        if result.per_person_delta:
            for group_name, deltas in result.per_person_delta.items():
                improvements = [p for p, d in deltas.items() if d > 0]
                declines = [p for p, d in deltas.items() if d < 0]
                if improvements:
                    result.recommendations.append(
                        f"{group_name}: {', '.join(improvements)} 口碑提升"
                    )
                if declines:
                    result.recommendations.append(
                        f"{group_name}: {', '.join(declines)} 口碑下降"
                    )

        return result

    def list_experiments(self) -> list[dict]:
        return [exp.to_dict() for exp in self.experiments.values()]

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self.experiments.get(experiment_id)
