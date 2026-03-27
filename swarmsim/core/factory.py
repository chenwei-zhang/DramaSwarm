"""
Agent Factory Module - Agent 生成器

根据种子信息自动生成具有独立人格的智能体。
"""

import random
import yaml
from pathlib import Path
from typing import Any

from swarmsim.core.agent import (
    Agent,
    AgentConfig,
    AgentRole,
    PersonalityProfile,
    SimpleAgent
)


class AgentFactory:
    """
    Agent 工厂

    根据模板和种子信息批量生成 Agent。
    """

    def __init__(self, templates_path: str | None = None):
        self.templates_path = templates_path
        self._templates: dict = {}
        self._name_counter: dict = {}

        if templates_path:
            self._load_templates(templates_path)

    def _load_templates(self, path: str) -> None:
        """加载人设模板"""
        template_file = Path(path)

        if template_file.suffix == ".yaml" or template_file.suffix == ".yml":
            with open(template_file, "r", encoding="utf-8") as f:
                self._templates = yaml.safe_load(f)

    def create(
        self,
        name: str,
        role: str | AgentRole,
        **kwargs
    ) -> Agent:
        """
        创建单个 Agent

        Args:
            name: Agent 名称
            role: 角色类型
            **kwargs: 其他配置参数

        Returns:
            Agent 实例
        """
        if isinstance(role, str):
            role = AgentRole(role)

        # 尝试从模板加载配置
        personality = self._get_personality_from_template(role, name)

        config = AgentConfig(
            name=name,
            role=role,
            personality=personality,
            **kwargs
        )

        return SimpleAgent(name=name, role=role, config=config, **kwargs)

    def create_from_dict(self, data: dict) -> Agent:
        """
        从字典创建 Agent

        Args:
            data: 包含 name, role, traits 等信息的字典

        Returns:
            Agent 实例
        """
        name = data.get("name", "Unknown")
        role_str = data.get("role", "custom")

        try:
            role = AgentRole(role_str)
        except ValueError:
            role = AgentRole.CUSTOM

        # 构建人格配置
        personality = PersonalityProfile(
            name=name,
            role=role,
            traits=data.get("traits", []),
            speech_style=data.get("speech_style", "neutral"),
            behavior_patterns=data.get("behavior_patterns", []),
            relationships=data.get("relationships", {}),
            system_prompt=data.get("system_prompt", "")
        )

        config = AgentConfig(
            name=name,
            role=role,
            personality=personality,
            model=data.get("model", "gpt-4o-mini"),
            temperature=data.get("temperature", 0.8)
        )

        return SimpleAgent(name=name, role=role, config=config)

    def create_batch(
        self,
        configs: list[dict],
        shuffle_names: bool = True
    ) -> list[Agent]:
        """
        批量创建 Agent

        Args:
            configs: 配置字典列表
            shuffle_names: 是否随机打乱顺序

        Returns:
            Agent 列表
        """
        agents = [self.create_from_dict(c) for c in configs]

        if shuffle_names:
            random.shuffle(agents)

        return agents

    def create_from_scenario(
        self,
        scenario: str,
        count: int = 5
    ) -> list[Agent]:
        """
        根据场景创建 Agent

        Args:
            scenario: 场景名称
            count: Agent 数量

        Returns:
            Agent 列表
        """
        scenario_templates = self._templates.get("scenarios", {}).get(scenario, {})
        role_distribution = scenario_templates.get("roles", None)

        if not role_distribution:
            # 默认随机角色
            roles = random.sample(list(AgentRole), min(count, len(AgentRole)))
        else:
            roles = [AgentRole(r) for r in role_distribution]

        agents = []
        for i, role in enumerate(roles[:count]):
            name = self._generate_name(role)
            agents.append(self.create(name, role))

        return agents

    def create_variety_show_cast(
        self,
        names: list[str],
        roles: list[str] | None = None,
        relationships: dict[tuple[str, str], str] | None = None
    ) -> list[Agent]:
        """
        创建综艺节目阵容

        Args:
            names: 参与者名称列表
            roles: 角色列表（与 names 一一对应）
            relationships: 关系配置，key 为 (name1, name2)，value 为关系类型

        Returns:
            Agent 列表
        """
        if roles is None:
            # 随机分配角色
            role_options = [r.value for r in AgentRole if r != AgentRole.CUSTOM]
            roles = [random.choice(role_options) for _ in names]

        agents = []
        for name, role_str in zip(names, roles):
            agent = self.create(name, role_str)
            agents.append(agent)

        # 设置关系
        if relationships:
            self._apply_relationships(agents, relationships)

        return agents

    def _get_personality_from_template(
        self,
        role: AgentRole,
        name: str
    ) -> PersonalityProfile:
        """从模板获取人格配置"""
        variety_show_templates = self._templates.get("variety_show", {})

        role_key = role.value
        if role_key not in variety_show_templates:
            return PersonalityProfile(name=name, role=role)

        template = variety_show_templates[role_key]

        # 解析特质
        traits = template.get("traits", [])
        behavior_patterns = template.get("behavior_patterns", [])
        speech_style = template.get("speech_style", "neutral")

        # 生成系统提示词
        system_prompt = self._build_system_prompt(template)

        return PersonalityProfile(
            name=name,
            role=role,
            traits=traits,
            speech_style=speech_style,
            behavior_patterns=behavior_patterns,
            system_prompt=system_prompt
        )

    def _build_system_prompt(self, template: dict) -> str:
        """构建系统提示词"""
        sections = []

        if "behavior_patterns" in template:
            patterns = template["behavior_patterns"]
            if isinstance(patterns, list):
                sections.append("行为模式:\n" + "\n".join(f"- {p}" for p in patterns))

        if "speech_style" in template:
            sections.append(f"说话风格: {template['speech_style']}")

        return "\n\n".join(sections)

    def _generate_name(self, role: AgentRole) -> str:
        """生成角色名称"""
        # 简单的名称生成器
        if role not in self._name_counter:
            self._name_counter[role] = 0

        self._name_counter[role] += 1
        count = self._name_counter[role]

        name_suffix = f"_{count}" if count > 1 else ""

        role_names = {
            AgentRole.LEADER: "组长",
            AgentRole.PEACEMAKER: "和事佬",
            AgentRole.DRAMA_QUEEN: "戏精",
            AgentRole.SLACKER: "摸鱼王",
            AgentRole.PERFECTIONIST: "完美主义",
            AgentRole.WILDCARD: "变数",
        }

        return role_names.get(role, "参与者") + name_suffix

    def _apply_relationships(
        self,
        agents: list[Agent],
        relationships: dict[tuple[str, str], str]
    ) -> None:
        """应用关系配置"""
        agent_map = {a.name: a for a in agents}

        for (name1, name2), relationship in relationships.items():
            agent1 = agent_map.get(name1)
            agent2 = agent_map.get(name2)

            if agent1 and agent2:
                agent1.set_relationship(agent2.id, relationship)
                agent2.set_relationship(agent1.id, relationship)

    def create_from_text_seed(
        self,
        text: str,
        count: int = 5,
        extract_entities: bool = True
    ) -> list[Agent]:
        """
        从文本种子创建 Agent

        Args:
            text: 种子文本（如小说、剧本片段）
            count: 要生成的 Agent 数量
            extract_entities: 是否尝试从文本提取实体

        Returns:
            Agent 列表
        """
        # 简化实现：随机生成
        # 实际应用中可以使用 NLP 提取实体和关系
        roles = random.sample(
            [r for r in AgentRole if r != AgentRole.CUSTOM],
            min(count, len(AgentRole) - 1)
        )

        agents = []
        for i, role in enumerate(roles):
            name = f"角色{i+1}"
            agent = self.create(name, role)
            # 添加初始记忆
            agent.memory.add(
                content=f"来源于文本: {text[:100]}...",
                source="seed",
                importance=0.8,
                tags=["origin"]
            )
            agents.append(agent)

        return agents


class VarietyShowFactory(AgentFactory):
    """
    综艺节目专用工厂

    预置了常见综艺节目的角色配置和关系模板。
    """

    # 经典综艺角色组合
    CAST_TEMPLATES = {
        "sisters_trip": {
            "name": "花儿与少年风格",
            "roles": ["leader", "perfectionist", "drama_queen", "slacker", "peacemaker"],
            "relationships": [
                (("组长", "完美主义"), "tension"),
                (("戏精", "摸鱼王"), "awkward"),
                (("和事佬", "组长"), "friendly"),
            ]
        },
        "dating_show": {
            "name": "恋爱观察风格",
            "roles": ["drama_queen", "wildcard", "peacemaker", "leader", "perfectionist"],
            "relationships": [
                (("戏精", "变数"), "tension"),
                (("和事佬", "组长"), "friendly"),
            ]
        },
        "roommate": {
            "name": "合租生活风格",
            "roles": ["leader", "slacker", "perfectionist", "peacemaker", "wildcard"],
            "relationships": [
                (("完美主义", "摸鱼王"), "tension"),
                (("组长", "和事佬"), "friendly"),
            ]
        }
    }

    def create_cast(self, template_name: str, names: list[str]) -> list[Agent]:
        """
        根据模板创建综艺阵容

        Args:
            template_name: 模板名称（sisters_trip, dating_show, roommate）
            names: 参与者名称列表

        Returns:
            Agent 列表
        """
        template = self.CAST_TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"未知模板: {template_name}")

        roles = template["roles"][:len(names)]
        relationships = template.get("relationships", [])

        # 创建角色映射
        role_map = dict(zip(names, roles))

        agents = []
        for name in names:
            role = role_map.get(name, "wildcard")
            agents.append(self.create(name, role))

        # 应用关系
        self._apply_template_relationships(agents, template.get("relationships", []))

        return agents

    def _apply_template_relationships(
        self,
        agents: list[Agent],
        relationships: list[tuple[tuple[str, str], str]]
    ) -> None:
        """应用模板关系"""
        agent_map = {a.name: a for a in agents}

        for (role1, role2), relationship in relationships:
            # 找到对应角色的 Agent
            agent1 = next((a for a in agents if a.role.value == role1), None)
            agent2 = next((a for a in agents if a.role.value == role2), None)

            if agent1 and agent2:
                agent1.set_relationship(agent2.id, relationship)
                agent2.set_relationship(agent1.id, relationship)


def create_variety_show_simulation(
    template: str = "sisters_trip",
    names: list[str] | None = None
) -> tuple[list[Agent], dict]:
    """
    便捷函数：创建综艺节目仿真

    Args:
        template: 模板名称
        names: 参与者名称

    Returns:
        (Agent 列表, 模拟配置)
    """
    if names is None:
        names = ["小张", "小李", "小王", "小赵", "小陈"]

    factory = VarietyShowFactory()
    agents = factory.create_cast(template, names)

    config = {
        "template": template,
        "names": names,
        "agent_count": len(agents)
    }

    return agents, config
