# -*- coding: utf-8 -*-
"""
结果分析器 - 仿真 vs 历史对比

对比仿真结果与真实历史数据，生成报告。
"""

from __future__ import annotations

from swarmsim.crisis.models import CrisisState, CrisisOutcomeReport, CrisisScenario


# ── 默认历史基线 ──

DEFAULT_BASELINES: dict[str, dict] = {
    "approval_floor": 30,      # 口谷最低值
    "final_approval": 50,      # 最终口碑
    "max_heat": 80,            # 最高热度
    "hot_duration": 10,        # 高热天数（heat > 60）
    "brand_loss": 30,          # 品牌价值损失
    "regulatory_peak": 3,      # 监管峰值
    "total_rumors": 5,         # 总谣言数
}


class OutcomeAnalyzer:
    """仿真结果分析器"""

    def analyze(
        self,
        state_history: list[CrisisState],
        scenario: CrisisScenario,
    ) -> CrisisOutcomeReport:
        """分析仿真结果并对比历史

        Args:
            state_history: 仿真状态历史
            scenario: 危机场景（含 historical_outcome）

        Returns:
            CrisisOutcomeReport
        """
        if not state_history:
            return CrisisOutcomeReport(
                verdict="no_data",
                verdict_label="无数据",
                summary="仿真未产生任何状态数据",
            )

        # 计算仿真指标
        sim_metrics = self._compute_metrics(state_history)

        # 获取历史基线
        historical = scenario.historical_outcome or {}

        # 对比
        comparison = self._compare_with_history(sim_metrics, historical, scenario)

        # 生成总结
        verdict, verdict_label = self._determine_verdict(comparison)

        summary = self._generate_summary(sim_metrics, historical, scenario)

        # PR 建议
        recommendations = self._generate_recommendations(sim_metrics, state_history)

        # 关键差异
        key_diffs = self._extract_key_differences(comparison)

        return CrisisOutcomeReport(
            verdict=verdict,
            verdict_label=verdict_label,
            summary=summary,
            metrics_comparison=comparison,
            pr_recommendations=recommendations,
            key_differences=key_diffs,
        )

    def _compute_metrics(self, history: list[CrisisState]) -> dict:
        """计算仿真核心指标"""
        if not history:
            return {}

        # 每人指标
        person_metrics: dict[str, dict] = {}
        all_names = set()
        for state in history:
            all_names.update(state.approval_scores.keys())

        for name in all_names:
            approvals = [s.approval_scores.get(name, 50) for s in history]
            brands = [s.brand_values.get(name, 50) for s in history]

            person_metrics[name] = {
                "min_approval": round(min(approvals), 1),
                "final_approval": round(approvals[-1], 1),
                "max_approval": round(max(approvals), 1),
                "approval_range": round(max(approvals) - min(approvals), 1),
                "min_brand": round(min(brands), 1),
                "final_brand": round(brands[-1], 1),
            }

        # 全局指标
        heats = [s.heat_index for s in history]
        hot_days = sum(1 for h in heats if h > 60)
        max_heat = max(heats) if heats else 0
        final_heat = heats[-1] if heats else 0
        total_rumors = history[-1].rumor_count if history else 0
        reg_peak = max(s.regulatory_level for s in history)

        return {
            "persons": person_metrics,
            "max_heat": round(max_heat, 1),
            "final_heat": round(final_heat, 1),
            "hot_search_duration": hot_days,
            "total_days": len(history),
            "total_rumors": total_rumors,
            "regulatory_peak": reg_peak,
        }

    def _compare_with_history(
        self,
        sim: dict,
        historical: dict,
        scenario: CrisisScenario,
    ) -> dict[str, dict]:
        """仿真 vs 历史对比"""
        comparison = {}
        sim_persons = sim.get("persons", {})

        for name in scenario.involved_persons:
            hist = historical.get(name, {})
            sp = sim_persons.get(name, {})

            hist_floor = hist.get("final_approval", DEFAULT_BASELINES["approval_floor"])
            hist_final = hist.get("final_approval", DEFAULT_BASELINES["final_approval"])

            sim_floor = sp.get("min_approval", 50)
            sim_final = sp.get("final_approval", 50)

            comparison[name] = {
                "sim_min_approval": sim_floor,
                "historical_final_approval": hist_floor,
                "sim_final_approval": sim_final,
                "historical_fate": hist.get("fate", "未知"),
                "historical_brand": hist.get("brand_status", "未知"),
                "sim_min_brand": sp.get("min_brand", 50),
                "sim_final_brand": sp.get("final_brand", 50),
                "approval_delta": round(sim_final - hist_final, 1),
                "better": sim_final > hist_final,
            }

        # 全局对比
        comparison["_global"] = {
            "sim_max_heat": sim.get("max_heat", 0),
            "sim_hot_days": sim.get("hot_search_duration", 0),
            "sim_rumors": sim.get("total_rumors", 0),
            "sim_regulatory_peak": sim.get("regulatory_peak", 0),
            "baseline_hot_days": DEFAULT_BASELINES["hot_duration"],
            "baseline_rumors": DEFAULT_BASELINES["total_rumors"],
        }

        return comparison

    def _determine_verdict(self, comparison: dict) -> tuple[str, str]:
        """判定仿真结果 vs 历史的好坏"""
        person_results = {k: v for k, v in comparison.items() if not k.startswith("_")}

        if not person_results:
            return "no_data", "无数据"

        better_count = sum(1 for v in person_results.values() if v.get("better"))
        total = len(person_results)

        if better_count == total:
            return "better", "仿真结果优于历史"
        elif better_count == 0:
            return "worse", "仿真结果劣于历史"
        else:
            return "mixed", "仿真结果好坏参半"

    def _generate_summary(
        self, sim: dict, historical: dict, scenario: CrisisScenario
    ) -> str:
        """生成文字总结"""
        lines = [f"危机场景：{scenario.title}，共模拟{sim.get('total_days', 0)}天。"]

        for name in scenario.involved_persons:
            sp = sim.get("persons", {}).get(name, {})
            hist = historical.get(name, {})
            min_ap = sp.get("min_approval", 50)
            final_ap = sp.get("final_approval", 50)
            fate = hist.get("fate", "未知")

            lines.append(
                f"{name}：仿真最低口碑{min_ap}，最终口碑{final_ap}；"
                f"历史结果：{fate}"
            )

        lines.append(
            f"最高热度：{sim.get('max_heat', 0)}，"
            f"高热天数：{sim.get('hot_search_duration', 0)}天，"
            f"总谣言数：{sim.get('total_rumors', 0)}。"
        )

        return "\n".join(lines)

    def _generate_recommendations(
        self, sim: dict, history: list[CrisisState]
    ) -> list[str]:
        """生成 PR 建议"""
        recs = []
        sim_persons = sim.get("persons", {})

        for name, metrics in sim_persons.items():
            min_ap = metrics.get("min_approval", 50)
            final_ap = metrics.get("final_approval", 50)

            if min_ap < 20:
                recs.append(f"{name}口碑跌至{min_ap}，建议在危机早期及时道歉")
            elif min_ap < 35:
                recs.append(f"{name}口碑一度跌至{min_ap}，发声明可能效果更好")

            if final_ap < 30:
                recs.append(f"{name}最终口碑仅{final_ap}，长期公益或复出计划可考虑")
            elif final_ap > 60:
                recs.append(f"{name}口碑恢复良好({final_ap})，策略基本有效")

        if sim.get("hot_search_duration", 0) > 10:
            recs.append("高热度持续时间过长，建议更早采取降温措施")

        if sim.get("total_rumors", 0) > 5:
            recs.append("谣言数量较多，沉默策略导致了信息真空")

        if sim.get("regulatory_peak", 0) >= 3:
            recs.append("监管压力较大，注意言行避免进一步升级")

        return recs[:8]

    def _extract_key_differences(self, comparison: dict) -> list[str]:
        """提取关键差异"""
        diffs = []
        for name, data in comparison.items():
            if name.startswith("_"):
                continue
            delta = data.get("approval_delta", 0)
            if delta > 10:
                diffs.append(f"{name}仿真口碑比历史高{delta}分")
            elif delta < -10:
                diffs.append(f"{name}仿真口碑比历史低{abs(delta)}分")

        global_data = comparison.get("_global", {})
        if global_data.get("sim_hot_days", 0) > 10:
            diffs.append(f"仿真中高热天数{global_data['sim_hot_days']}天，持续较长")

        return diffs[:6]
