# -*- coding: utf-8 -*-
"""
危机仿真 CLI Demo

纯规则模式，无需 API key。
用法: python -m demos.crisis_simulation
"""

from __future__ import annotations

import asyncio
import sys
import os

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarmsim.graph.temporal import TemporalKnowledgeGraph
from swarmsim.crisis.scenario_engine import CrisisScenarioEngine
from swarmsim.crisis.outcome_analyzer import OutcomeAnalyzer


def load_graph() -> TemporalKnowledgeGraph:
    """加载知识图谱"""
    kg = TemporalKnowledgeGraph()

    # 尝试从 JSON 加载
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "celebrity_scraper", "data"
    )
    if os.path.exists(data_dir):
        stats = kg.load_from_json_dir(data_dir)
        if stats["celebrities"] > 0:
            return kg

    # 降级到 mock
    names = ["肖战", "王一博", "杨幂", "赵丽颖", "迪丽热巴",
             "李小璐", "贾乃亮", "PG One", "唐嫣", "罗晋"]
    stats = kg.load_from_mock_data(names)
    print(f"[Mock] 加载: {stats['celebrities']}位明星, "
          f"{stats['relationships']}条关系, {stats['gossips']}个事件")
    return kg


def print_separator(char: str = "─", width: int = 60):
    print(char * width)


async def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║              DramaSwarm 危机仿真引擎 Demo                  ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # 加载图谱
    print("加载知识图谱...")
    kg = load_graph()
    print(f"图谱统计: {kg.node_count}节点, {kg.edge_count}边")
    print()

    # 创建引擎
    engine = CrisisScenarioEngine(kg)
    scenarios = engine.list_scenarios()

    if not scenarios:
        print("未找到可用的危机场景！")
        return

    # 列出场景
    print("可用危机场景:")
    print_separator()
    for i, s in enumerate(scenarios):
        hist_mark = " [有历史基线]" if s["has_historical"] else ""
        print(f"  {i+1}. {s['title']} ({s['date']}) "
              f"- 严重度 {s['importance']:.1f}{hist_mark}")
        print(f"     涉及: {', '.join(s['involved_persons'])}")
    print()

    # 选择场景
    target = None
    for s in scenarios:
        if "夜宿" in s["title"] or "做头发" in s["title"]:
            target = s["title"]
            break
    if not target:
        target = scenarios[0]["title"]

    print(f"选择场景: {target}")
    print_separator()

    # 创建仿真
    sim = engine.create_simulation(
        scenario_title=target,
        use_llm=False,
        total_days=30,
    )
    print(f"场景: {sim.scenario.title}")
    print(f"涉及人物: {', '.join(sim.scenario.involved_persons)}")
    print(f"初始严重度: {sim.scenario.initial_severity:.1f}")
    print()

    # 初始状态
    state = sim.get_state()
    print("初始状态:")
    for name in sim.scenario.involved_persons:
        ap = state.approval_scores.get(name, 50)
        print(f"  {name}: 口碑 {ap:.0f}/100")
    print(f"  热度: {state.heat_index:.0f}/100")
    print()

    # 运行
    print("开始仿真 (30天)...")
    print_separator()

    for day in range(30):
        state = await sim.step()
        phase = state.phase

        # 打印每日摘要
        print(f"\n📅 第{state.day}天 [{phase.label}] {sim.timeline.current_date()}")
        print(f"   热度: {state.heat_index:.0f} | 谣言: {state.rumor_count} | 监管: Lv.{state.regulatory_level}")

        for action in state.agent_actions:
            print(f"   🎭 {action.actor} → {action.action.label}")

        for rumor in (state.rumors or [])[-2:]:
            if rumor.get("day") == state.day:
                print(f"   💬 谣言: {rumor['content']}")

        # 口碑变化
        for name in sim.scenario.involved_persons:
            ap = state.approval_scores.get(name, 50)
            delta = ""
            if len(sim.state_history) >= 2:
                prev = sim.state_history[-2].approval_scores.get(name, 50)
                d = ap - prev
                if abs(d) > 0.5:
                    delta = f" ({'+' if d > 0 else ''}{d:.1f})"
            print(f"   📊 {name}: {ap:.0f}{delta}")

        if sim.is_finished():
            break

    # 结果分析
    print()
    print_separator("═")
    print("仿真结束，生成结果报告...")
    print_separator("═")

    analyzer = OutcomeAnalyzer()
    report = analyzer.analyze(sim.state_history, sim.scenario)

    print(f"\n📋 结论: {report.verdict_label}")
    print(f"\n{report.summary}")

    if report.metrics_comparison:
        print("\n📊 详细对比:")
        for name, data in report.metrics_comparison.items():
            if name.startswith("_"):
                continue
            if isinstance(data, dict):
                print(f"\n  {name}:")
                for k, v in data.items():
                    if isinstance(v, float):
                        v = f"{v:.1f}"
                    print(f"    {k}: {v}")

    if report.pr_recommendations:
        print("\n💡 PR 建议:")
        for rec in report.pr_recommendations:
            print(f"  • {rec}")

    if report.key_differences:
        print("\n🔍 关键差异:")
        for diff in report.key_differences:
            print(f"  • {diff}")


if __name__ == "__main__":
    asyncio.run(main())
