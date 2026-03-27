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
from swarmsim.graph import KnowledgeGraph


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

        # 加载知识图谱
        self._load_knowledge_graph()

        # 创建 Agent
        self.agents = self._create_agents()

        # 创建事件循环（从环境变量读取配置）
        config = EventLoopConfig(
            tick_interval=float(os.getenv("SIMULATION_TICK_INTERVAL", "0.5")),
            max_turns=20,
            agents_per_turn=len(names),  # 所有 agent 每回合都行动
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

    def _load_knowledge_graph(self):
        """从爬虫数据加载知识图谱"""
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "celebrity_scraper", "data"
        )
        if os.path.exists(data_dir):
            kg = KnowledgeGraph()
            stats = kg.load_from_json_dir(data_dir)
            if stats["celebrities"] > 0:
                self.environment.knowledge_graph = kg
                self.console.print(
                    f"[dim]知识图谱已加载: {stats['celebrities']}位明星, "
                    f"{stats['relationships']}条关系, {stats['gossips']}个事件[/dim]"
                )

    def _create_agents(self) -> list:
        """创建 Agent 列表"""
        factory = VarietyShowFactory()

        # 首先获取角色分配
        template_info = factory.CAST_TEMPLATES.get(self.template, {})
        base_roles = template_info.get("roles", ["leader", "perfectionist", "drama_queen", "slacker", "peacemaker"])

        # 如果 agent 数量超过角色数量，循环分配角色
        roles = [base_roles[i % len(base_roles)] for i in range(len(self.names))]

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

        async def on_turn_end(turn_number, result):
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

        # 显示反应层摘要
        reaction_desc = self.environment.reaction_bus.get_description()
        if reaction_desc.strip():
            self.console.print(Panel(
                reaction_desc,
                title="[bold magenta]社会反应[/bold magenta]",
                border_style="dim",
                padding=(0, 1),
            ))

    async def run(self, turns: int = 10):
        """运行仿真"""
        self._print_intro()

        # 设置初始任务 - 八瓜话题
        topic = """今天录制闲聊环节，话题是当年的娱乐圈大瓜：李小璐、贾乃亮、PG One三角恋事件。

背景：2017年，李小璐被拍到与说唱歌手PG One深夜亲密互动，引发轰动。随后贾乃亮在直播中说"相信我老婆"，但最终还是离婚收场。这件事至今仍是娱乐圈的热门讨论话题。"""

        self.environment.set_task(topic, deadline_hours=2)

        # 广播背景信息
        self.environment.broadcast(
            "导演组宣布：今天咱们不聊工作，就聊八卦！大家对李小璐贾乃亮PG One这事怎么看？",
            source="director",
            importance=0.9
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

        # 反应系统最终状态
        reaction_state = self.environment.reaction_bus.get_state()

        # 热搜历史
        hot_search = reaction_state.get("social_platform", {}).get("hot_search", [])
        if hot_search:
            self.console.print("\n[bold]最终热搜榜:[/bold]")
            for t in hot_search[:5]:
                change_icon = {"rising": "↑", "falling": "↓", "new_entry": "★"}.get(t.get("change", ""), "→")
                self.console.print(f"  {t['rank']}. {change_icon} {t['title']} (热度{t['heat'] // 1000}k)")

        # 品牌状态
        brand_statuses = reaction_state.get("commercial", {}).get("brand_statuses", {})
        if brand_statuses:
            self.console.print("\n[bold]品牌代言状态:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("明星", style="cyan")
            table.add_column("商业价值", style="green")
            table.add_column("品牌状态", style="yellow")
            table.add_column("收入影响", style="red")
            for name, status in brand_statuses.items():
                brands_str = ", ".join(f"{b}:{a}" for b, a in status.get("brands", {}).items())
                table.add_row(name, status.get("commercial_value", "?"), brands_str, status.get("revenue_impact", "0"))
            self.console.print(table)


async def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="综艺节目修罗场模拟")
    parser.add_argument("--llm", action="store_true", help="使用 LLM 驱动 Agent")
    parser.add_argument("--provider", default="gemini", help="LLM 提供商 (gemini, openai, anthropic)")
    parser.add_argument("--model", help="LLM 模型名称")
    parser.add_argument("--turns", type=int, default=int(os.getenv("DEFAULT_TURNS", "15")), help="仿真回合数")
    parser.add_argument("--agents", type=int, default=int(os.getenv("MAX_AGENTS", "5")), help="Agent 数量")
    parser.add_argument("--names", nargs="+", help="自定义 Agent 名称列表")
    args = parser.parse_args()

    # 定义参与成员
    if args.names:
        names = args.names
    else:
        # 默认名称生成（动态生成足够多的名字）
        base_names = [
            "队长张三", "完美主义李四", "戏精王五", "摸鱼赵六", "和事佬孙七",
            "变数阿八", "实干家小九", "乐天派小十"
        ]
        # 如果需要更多名字，自动生成
        while len(base_names) < args.agents:
            num = len(base_names) + 1
            base_names.append(f"成员{num}")

        names = base_names[:args.agents]

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
