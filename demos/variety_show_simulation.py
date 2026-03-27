"""
Variety Show Simulation Demo - 综艺节目修罗场模拟

模拟一档类似《花儿与少年》的综艺节目，
观察性格各异的明星在密闭空间、预算限制下的互动。
"""

import asyncio
import os
import sys
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from swarmsim.core.agent import SimpleAgent, LLMAgent, AgentRole, create_agent
from swarmsim.core.environment import VarietyShowEnvironment
from swarmsim.core.event_loop import SequentialEventLoop, EventLoopConfig
from swarmsim.core.factory import VarietyShowFactory
from swarmsim.core.observer import Observer, Reporter


class VarietyShowSimulation:
    """综艺节目仿真主程序"""

    def __init__(
        self,
        names: list[str],
        template: str = "sisters_trip",
        use_llm: bool = False,
        llm_provider: str = "gemini",
        llm_model: str | None = None
    ):
        self.console = Console()
        self.names = names
        self.template = template
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self.llm_model = llm_model

        # 创建环境
        self.environment = VarietyShowEnvironment(
            name="综艺修罗场",
            initial_budget=1000.0,
            task_complexity=0.6
        )

        # 创建 Agent
        self.agents = self._create_agents()

        # 创建事件循环
        config = EventLoopConfig(
            tick_interval=0.5,
            max_turns=20,
            agents_per_turn=len(names),
            enable_parallel=False
        )
        self.event_loop = SequentialEventLoop(self.environment, config)

        # 添加 Agent 到循环
        for agent in self.agents:
            self.event_loop.add_agent(agent)

        # 创建观测者
        self.observer = Observer()
        self.reporter = Reporter(self.observer)

        # 设置回调
        self._setup_callbacks()

    def _create_agents(self) -> list:
        """创建 Agent 列表"""
        factory = VarietyShowFactory()

        # 首先获取角色分配
        template_info = factory.CAST_TEMPLATES.get(self.template, {})
        roles = template_info.get("roles", ["leader", "perfectionist", "drama_queen", "slacker", "peacemaker"])
        roles = roles[:len(self.names)]

        agents = []
        for name, role_str in zip(self.names, roles):
            if self.use_llm:
                agent = LLMAgent(
                    name=name,
                    role=AgentRole(role_str),
                    llm_provider=self.llm_provider,
                    llm_model=self.llm_model
                )
            else:
                agent = SimpleAgent(name=name, role=AgentRole(role_str))
            agents.append(agent)

        # 应用关系
        relationships = template_info.get("relationships", [])
        factory._apply_template_relationships(agents, relationships)

        return agents

    def _setup_callbacks(self):
        """设置回调函数"""
        def on_action(action):
            """行动回调"""
            self.observer.observe_action(action.to_dict())

        def on_turn_end(turn_number, result):
            """回合结束回调"""
            self.observer.observe_turn(result)
            self._print_turn_summary(turn_number, result)

        self.event_loop.on_action = on_action
        self.event_loop.on_turn_end = on_turn_end

    def _print_turn_summary(self, turn_number: int, result):
        """打印回合摘要"""
        self.console.print(f"\n--- 第 {turn_number} 回合 ---", style="bold cyan")

        for action in result.actions:
            agent_name = action.agent_name
            content = action.content

            if action.action_type == "speak":
                self.console.print(
                    f"[bold yellow]{agent_name}:[/bold yellow] {content}"
                )
            elif action.action_type == "act":
                self.console.print(
                    f"[dim]* {agent_name} {content}[/dim]"
                )

    async def run(self, turns: int = 10):
        """运行仿真"""
        self._print_intro()

        # 设置初始任务
        self.environment.set_task(
            "在预算有限的情况下，团队需要决定晚餐吃什么。",
            deadline_hours=24
        )

        # 运行
        await self.event_loop.run(max_turns=turns)

        # 生成报告
        self._print_final_report()

    def _print_intro(self):
        """打印开场"""
        intro = f"""
[bold magenta]╔════════════════════════════════════════╗
║     综艺节目修罗场模拟器 v1.0        ║
╚════════════════════════════════════════╝[/bold magenta]

[bold]参与成员:[/bold]
"""
        for agent in self.agents:
            role_emoji = {
                AgentRole.LEADER: "👑",
                AgentRole.PEACEMAKER: "🤝",
                AgentRole.DRAMA_QUEEN: "🎭",
                AgentRole.SLACKER: "😴",
                AgentRole.PERFECTIONIST: "📏",
                AgentRole.WILDCARD: "🎲",
            }.get(agent.role, "👤")

            self.console.print(
                f"  {role_emoji} {agent.name} - {agent.role.value}"
            )

        self.console.print()

        # 打印环境信息
        env_panel = Panel(
            self.environment.get_description(),
            title="[bold green]当前环境[/bold green]",
            border_style="green"
        )
        self.console.print(env_panel)

    def _print_final_report(self):
        """打印最终报告"""
        self.console.print("\n")
        self.console.print(
            Panel(
                "[bold red]═════════════════════════════════════\n"
                "           仿真结束 - 观测报告\n"
                "═════════════════════════════════════[/bold red]",
                style="red"
            )
        )

        # 群体动态分析
        dynamics = self.observer.analyze_group_dynamics()

        # 和谐度
        harmony_score = dynamics["metrics"]["harmony_score"]
        harmony_color = "green" if harmony_score > 0.6 else "yellow" if harmony_score > 0.3 else "red"
        self.console.print(
            f"[bold]群体和谐度:[/bold] [{harmony_color}]{harmony_score:.2%}[/{harmony_color}]"
        )

        # 参与度排名
        self.console.print("\n[bold]参与度排名:[/bold]")
        for i, (agent_id, count) in enumerate(dynamics["participation_ranking"], 1):
            # 尝试从 Agent 列表中查找名称
            agent = next((a for a in self.agents if a.id == agent_id), None)
            # 如果找不到，可能存储的是 agent_name 而不是 id
            if not agent:
                agent = next((a for a in self.agents if a.name == agent_id), None)
            name = agent.name if agent else agent_id
            self.console.print(f"  {i}. {name}: {count} 次互动")

        # Agent 状态
        self.console.print("\n[bold]最终状态:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("成员", style="cyan")
        table.add_column("状态", style="yellow")
        table.add_column("压力", style="red")
        table.add_column("精力", style="green")
        table.add_column("记忆数", style="blue")

        for agent in self.agents:
            state_emoji = {
                "idle": "😊",
                "thinking": "🤔",
                "speaking": "💬",
                "listening": "👂",
                "acting": "🎬",
                "stressed": "😫",
                "withdrawn": "🙍",
            }.get(agent.state.value, "❓")

            stress_bar = "█" * int(agent.stress_level * 5) + "░" * (5 - int(agent.stress_level * 5))
            energy_bar = "█" * int(agent.energy_level * 5) + "░" * (5 - int(agent.energy_level * 5))

            table.add_row(
                agent.name,
                f"{state_emoji} {agent.state.value}",
                f"[red]{stress_bar}[/red] {agent.stress_level:.1f}",
                f"[green]{energy_bar}[/green] {agent.energy_level:.1f}",
                str(len(agent.memory.memories))
            )

        self.console.print(table)

        # 关键事件
        critical_events = [
            o for o in self.observer.observations if o.importance > 0.7
        ]
        if critical_events:
            self.console.print("\n[bold yellow]关键事件:[/bold yellow]")
            for event in critical_events[-5:]:
                self.console.print(f"  • {event.description}")

        # 叙事总结
        self.console.print("\n[bold]叙事总结:[/bold]")
        narrative = self.reporter.generate_narrative()
        self.console.print(Panel(narrative, border_style="dim"))

        # 环境状态
        self.console.print("\n[bold]环境状态:[/bold]")
        self.console.print(Panel(
            self.environment.get_description(),
            border_style="dim"
        ))


async def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="综艺节目修罗场模拟")
    parser.add_argument("--llm", action="store_true", help="使用 LLM 驱动 Agent")
    parser.add_argument("--provider", default="gemini", help="LLM 提供商 (gemini, openai, anthropic)")
    parser.add_argument("--model", help="LLM 模型名称")
    parser.add_argument("--turns", type=int, default=15, help="仿真回合数")
    args = parser.parse_args()

    # 定义参与成员
    names = [
        "队长张三",
        "完美主义李四",
        "戏精王五",
        "摸鱼赵六",
        "和事佬孙七"
    ]

    # 显示 LLM 状态
    if args.llm:
        provider = args.provider
        model = args.model or os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
        print(f"🤖 使用 LLM: {provider} ({model})")
    else:
        print("📝 使用规则引擎（快速模式）")

    # 创建并运行仿真
    sim = VarietyShowSimulation(
        names,
        template="sisters_trip",
        use_llm=args.llm,
        llm_provider=args.provider,
        llm_model=args.model
    )
    await sim.run(turns=args.turns)


if __name__ == "__main__":
    asyncio.run(main())
