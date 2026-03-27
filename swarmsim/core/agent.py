"""
Core Agent Module - 智能体核心模块

定义 Agent 基类、状态管理和决策逻辑。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRole(Enum):
    """Agent 角色类型"""
    LEADER = "leader"
    PEACEMAKER = "peacemaker"
    DRAMA_QUEEN = "drama_queen"
    SLACKER = "slacker"
    PERFECTIONIST = "perfectionist"
    WILDCARD = "wildcard"
    CUSTOM = "custom"


class AgentState(Enum):
    """Agent 状态枚举"""
    IDLE = "idle"           # 空闲，等待行动
    THINKING = "thinking"   # 思考中
    SPEAKING = "speaking"   # 发言中
    LISTENING = "listening" # 倾听中
    ACTING = "acting"       # 执行行动
    STRESSED = "stressed"   # 压力状态
    WITHDRAWN = "withdrawn" # 退缩状态


@dataclass
class Memory:
    """单条记忆数据结构"""
    timestamp: datetime
    content: str
    source: str  # 记忆来源：agent_id, environment, system
    importance: float = 0.5  # 重要性评分 0-1
    tags: list[str] = field(default_factory=list)

    def decay(self, rate: float = 0.1) -> float:
        """计算记忆衰减后的重要性"""
        return max(0, self.importance * (1 - rate))


class AgentMemory:
    """
    Agent 记忆管理系统

    维护短期记忆（当前会话）和长期记忆（跨会话持久化）。
    实现记忆检索、衰减和优先级排序。
    """

    def __init__(self, retention_turns: int = 10):
        self.memories: list[Memory] = []
        self.retention_turns = retention_turns
        self.current_turn = 0

    def add(
        self,
        content: str,
        source: str,
        importance: float = 0.5,
        tags: list[str] | None = None
    ) -> None:
        """添加新记忆"""
        memory = Memory(
            timestamp=datetime.now(),
            content=content,
            source=source,
            importance=importance,
            tags=tags or []
        )
        self.memories.append(memory)
        self._cleanup()

    def get_recent(self, n: int = 5) -> list[Memory]:
        """获取最近的记忆"""
        return self.memories[-n:]

    def get_important(self, threshold: float = 0.6, n: int = 10) -> list[Memory]:
        """获取重要记忆"""
        filtered = [m for m in self.memories if m.importance >= threshold]
        return sorted(filtered, key=lambda m: m.importance, reverse=True)[:n]

    def search(self, query: str, n: int = 5) -> list[Memory]:
        """简单关键词搜索记忆"""
        query_lower = query.lower()
        results = [
            m for m in self.memories
            if query_lower in m.content.lower() or
               any(query_lower in tag.lower() for tag in m.tags)
        ]
        return results[:n]

    def _cleanup(self) -> None:
        """清理过期记忆"""
        if len(self.memories) > self.retention_turns * 10:
            # 保留重要记忆和最近的记忆
            important = [m for m in self.memories if m.importance > 0.7]
            recent = self.memories[-self.retention_turns:]
            self.memories = important + recent

    def advance_turn(self) -> None:
        """推进回合，衰减记忆重要性"""
        self.current_turn += 1
        for memory in self.memories:
            memory.importance = memory.decay(rate=0.05)
        self._cleanup()

    def get_context_summary(self, max_tokens: int = 500) -> str:
        """生成用于 LLM 的上下文摘要"""
        recent = self.get_recent(3)
        important = [m for m in self.get_important(0.6, 3) if m not in recent]

        context_parts = []
        for memory in recent + important:
            context_parts.append(f"[{memory.source}] {memory.content}")

        return " | ".join(context_parts)


class PersonalityProfile(BaseModel):
    """人格特征配置"""

    name: str = Field(description="Agent 名称")
    role: AgentRole = Field(description="角色类型")

    # Big Five 人格特质 (0-1)
    openness: float = Field(default=0.5, ge=0, le=1)
    conscientiousness: float = Field(default=0.5, ge=0, le=1)
    extraversion: float = Field(default=0.5, ge=0, le=1)
    agreeableness: float = Field(default=0.5, ge=0, le=1)
    neuroticism: float = Field(default=0.5, ge=0, le=1)

    # 行为倾向
    traits: list[str] = Field(default_factory=list)
    speech_style: str = Field(default="neutral")
    behavior_patterns: list[str] = Field(default_factory=list)

    # 关系配置
    relationships: dict[str, str] = Field(
        default_factory=dict,
        description="与其他 Agent 的关系，key 为 agent_id"
    )

    # 系统提示词
    system_prompt: str = Field(default="")


class AgentConfig(BaseModel):
    """Agent 配置类"""

    # 基础信息
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    role: AgentRole

    # LLM 配置
    model: str = "gpt-4o-mini"
    temperature: float = 0.8

    # 记忆配置
    memory_retention_turns: int = 10

    # 人格配置
    personality: PersonalityProfile | None = None


class Agent:
    """
    智能体核心类

    每个 Agent 拥有独立的人格、记忆和决策能力。
    通过 LLM 驱动生成自然语言响应。
    """

    def __init__(self, config: AgentConfig):
        self.id = config.id
        self.name = config.name
        self.role = config.role
        self.model = config.model
        self.temperature = config.temperature

        # 人格配置
        self.personality = config.personality or self._default_personality()

        # 状态管理
        self.state = AgentState.IDLE
        self.stress_level = 0.0  # 0-1
        self.energy_level = 1.0  # 0-1

        # 记忆系统
        self.memory = AgentMemory(retention_turns=config.memory_retention_turns)

        # 回调函数
        self.on_speak: Callable | None = None
        self.on_act: Callable | None = None
        self.on_state_change: Callable | None = None

    def _default_personality(self) -> PersonalityProfile:
        """创建默认人格配置"""
        return PersonalityProfile(
            name=self.name,
            role=self.role
        )

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        base_prompt = f"""你是 {self.name}，一个在多智能体仿真环境中的角色。

角色类型: {self.role.value}
性格特征: {", ".join(self.personality.traits)}
说话风格: {self.personality.speech_style}

请根据你的人格特征和当前情境做出自然、真实的反应。
不要扮演 AI 助手，而是完全代入这个角色。
"""
        if self.personality.system_prompt:
            base_prompt += f"\n{self.personality.system_prompt}"

        return base_prompt

    def get_state_description(self) -> str:
        """获取当前状态描述"""
        stress_desc = "平静"
        if self.stress_level > 0.7:
            stress_desc = "非常紧张"
        elif self.stress_level > 0.4:
            stress_desc = "有些压力"

        energy_desc = "精力充沛"
        if self.energy_level < 0.3:
            energy_desc = "精疲力竭"
        elif self.energy_level < 0.6:
            energy_desc = "有些疲惫"

        return f"状态: {self.state.value} | 压力: {stress_desc} | 精力: {energy_desc}"

    def perceive(self, event: dict) -> None:
        """
        感知环境事件

        Args:
            event: 事件字典，包含 type, source, content 等字段
        """
        event_type = event.get("type", "unknown")
        content = event.get("content", "")
        source = event.get("source", "environment")

        # 根据事件类型和性格决定记忆重要性
        importance = 0.5
        if event_type in ["conflict", "criticism"]:
            if self.personality.neuroticism > 0.6:
                importance = 0.8
        elif event_type in ["praise", "agreement"]:
            if self.personality.extraversion > 0.6:
                importance = 0.6

        self.memory.add(
            content=f"{event_type}: {content}",
            source=source,
            importance=importance,
            tags=[event_type]
        )

    async def think(self, context: dict) -> str:
        """
        思考并生成决策

        Args:
            context: 当前情境信息

        Returns:
            思考结果/内心独白
        """
        self.state = AgentState.THINKING
        self._notify_state_change()

        # 简单决策逻辑（可以替换为 LLM 调用）
        thoughts = []

        # 基于性格的反应
        if self.stress_level > 0.7:
            if self.personality.neuroticism > 0.6:
                thoughts.append("这情况太糟糕了...")
            else:
                thoughts.append("需要冷静处理这个情况。")

        # 基于记忆的反应
        recent_memory = self.memory.get_context_summary()
        if recent_memory:
            thoughts.append(f"我记得: {recent_memory}")

        result = " | ".join(thoughts) if thoughts else "观察当前情况..."

        self.state = AgentState.IDLE
        self._notify_state_change()

        return result

    async def speak(self, context: dict, prompt: str | None = None) -> str:
        """
        生成发言内容

        Args:
            context: 当前情境信息
            prompt: 可选的外部提示

        Returns:
            发言内容
        """
        self.state = AgentState.SPEAKING
        self._notify_state_change()

        # 构建完整的提示
        system_prompt = self.get_system_prompt()
        memory_context = self.memory.get_context_summary()

        full_prompt = f"""当前情况: {context}
最近的记忆: {memory_context}"""

        if prompt:
            full_prompt += f"\n需要回应的内容: {prompt}"

        # 这里可以调用 LLM，暂时使用简单的基于规则的响应
        response = await self._generate_response(full_prompt)

        # 记录自己的发言
        self.memory.add(
            content=f"我说: {response}",
            source="self",
            importance=0.6,
            tags=["speech"]
        )

        self.state = AgentState.IDLE
        self._notify_state_change()

        return response

    async def _generate_response(self, prompt: str) -> str:
        """
        生成响应（可替换为实际 LLM 调用）

        这是一个简化的实现，实际使用时应该调用 LLM API
        """
        # 简单的基于规则的响应（Phase 1）
        responses_by_role = {
            AgentRole.LEADER: [
                "我认为我们应该这样做...",
                "让我来处理这个情况。",
                "大家先听我说。"
            ],
            AgentRole.PEACEMAKER: [
                "也许我们可以各退一步？",
                "大家别激动，有话好好说。",
                "我理解大家的想法..."
            ],
            AgentRole.DRAMA_QUEEN: [
                "这真是太让人难以置信了！",
                "我完全无法接受这种情况！",
                "你们知道我是什么感受吗？！"
            ],
            AgentRole.SLACKER: [
                "随便啦，都可以。",
                "嗯...你们决定吧。",
                "这事儿不用急吧..."
            ],
            AgentRole.PERFECTIONIST: [
                "这里有个问题需要注意。",
                "我觉得这样不太对...",
                "我们需要更仔细地考虑。"
            ],
            AgentRole.WILDCARD: [
                "我们要不要试试完全不同的方法？",
                "说起来，我有个有趣的想法...",
                "如果从另一个角度看呢？"
            ]
        }

        import random
        responses = responses_by_role.get(
            self.role,
            ["好的，我明白了。", "嗯...", "有意思。"]
        )
        return random.choice(responses)

    async def act(self, context: dict) -> dict:
        """
        执行行动

        Args:
            context: 当前情境信息

        Returns:
            行动描述字典
        """
        self.state = AgentState.ACTING
        self._notify_state_change()

        # 行动会消耗精力
        self.energy_level = max(0, self.energy_level - 0.1)

        action = {
            "agent_id": self.id,
            "agent_name": self.name,
            "type": "wait",
            "description": f"{self.name} 正在观察...",
            "timestamp": datetime.now().isoformat()
        }

        self.state = AgentState.IDLE
        self._notify_state_change()

        return action

    def listen(self, speaker_id: str, content: str) -> None:
        """
        倾听他人发言

        Args:
            speaker_id: 发言者 ID
            content: 发言内容
        """
        self.state = AgentState.LISTENING

        # 根据与发言者的关系调整记忆重要性
        relationship = self.personality.relationships.get(speaker_id, "neutral")
        importance = 0.5

        if relationship in ["rival", "tension"]:
            importance = 0.7  # 对对手的话更敏感
        elif relationship in ["friendly", "mentor_mentee"]:
            importance = 0.6  # 对朋友的话更在意

        self.memory.add(
            content=f"{speaker_id} 说: {content}",
            source=speaker_id,
            importance=importance,
            tags=["listening", speaker_id]
        )

        self.state = AgentState.IDLE

    def update_stress(self, delta: float) -> None:
        """更新压力水平"""
        self.stress_level = max(0, min(1, self.stress_level + delta))

    def update_energy(self, delta: float) -> None:
        """更新精力水平"""
        self.energy_level = max(0, min(1, self.energy_level + delta))

    def set_relationship(self, other_id: str, relationship: str) -> None:
        """设置与其他 Agent 的关系"""
        self.personality.relationships[other_id] = relationship

    def _notify_state_change(self) -> None:
        """通知状态变化"""
        if self.on_state_change:
            self.on_state_change(self.id, self.state)

    def reset(self) -> None:
        """重置 Agent 状态"""
        self.state = AgentState.IDLE
        self.stress_level = 0.0
        self.energy_level = 1.0
        self.memory = AgentMemory(retention_turns=self.memory.retention_turns)

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "state": self.state.value,
            "stress_level": self.stress_level,
            "energy_level": self.energy_level,
            "personality": {
                "traits": self.personality.traits,
                "speech_style": self.personality.speech_style
            },
            "memory_count": len(self.memory.memories)
        }

    def __repr__(self) -> str:
        return f"Agent(id={self.id[:8]}..., name={self.name}, role={self.role.value})"


class SimpleAgent(Agent):
    """
    简化版 Agent，用于快速原型和测试

    不依赖 LLM API，使用基于规则的响应。
    """

    def __init__(self, name: str, role: AgentRole, **kwargs):
        config = AgentConfig(
            name=name,
            role=role,
            **kwargs
        )
        super().__init__(config)

    async def speak(self, context: dict, prompt: str | None = None) -> str:
        """生成基于规则的发言"""
        self.state = AgentState.SPEAKING

        # 根据角色生成响应
        responses = {
            AgentRole.LEADER: [
                f"大家好，作为{self.name}，我认为我们应该...",
                "让我来组织一下接下来的计划。",
                "我们需要一个明确的方向。"
            ],
            AgentRole.PEACEMAKER: [
                "大家别激动，我们可以好好商量。",
                "我理解双方的想法...",
                "或许有个折中的方案？"
            ],
            AgentRole.DRAMA_QUEEN: [
                "你们知道我现在什么感受吗？！",
                "这简直太不可思议了！",
                "我真的无法接受这种情况！"
            ],
            AgentRole.SLACKER: [
                "嗯...你们定吧，我都可以。",
                "这事儿不急吧...",
                "我没什么意见。"
            ],
            AgentRole.PERFECTIONIST: [
                "等等，这个细节需要注意。",
                "我觉得我们需要更仔细地考虑。",
                "这样做可能会有问题..."
            ],
            AgentRole.WILDCARD: [
                "说起来，要不要试试完全不同的思路？",
                "我突然有个想法...",
                "如果从另一个角度看呢？"
            ]
        }

        import random
        response = random.choice(responses.get(self.role, ["好的。"]))

        self.memory.add(
            content=f"我说: {response}",
            source="self",
            importance=0.5
        )

        self.state = AgentState.IDLE
        return response


class LLMAgent(Agent):
    """
    使用 LLM 驱动的 Agent

    通过 LLM API 生成更智能、更自然的响应。
    支持多种 LLM 提供商（Gemini, OpenAI, Anthropic 等）。
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        llm_client: Any = None,
        llm_provider: str = "gemini",
        llm_model: str | None = None,
        **kwargs
    ):
        # 创建配置
        config = AgentConfig(
            name=name,
            role=role,
            **kwargs
        )

        super().__init__(config)

        # LLM 配置
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self._llm_client = llm_client
        self._conversation_history: list[tuple[str, str]] = []  # (role, content)

    @property
    def llm_client(self) -> Any:
        """延迟加载 LLM 客户端"""
        if self._llm_client is None:
            from swarmsim.llm import get_client
            self._llm_client = get_client(
                provider=self.llm_provider,
                model=self.llm_model
            )
        return self._llm_client

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        base_prompt = f"""你是 {self.name}，一个在多智能体仿真环境中的角色。

【角色类型】
{self.role.value}

【性格特征】
{', '.join(self.personality.traits)}

【说话风格】
{self.personality.speech_style}

【行为模式】
{chr(10).join(f'- {p}' for p in self.personality.behavior_patterns[:5])}

【重要规则】
1. 完全代入角色，不要扮演 AI 助手
2. 回复要简洁自然，通常不超过 50 字
3. 根据你的性格特征做出符合人设的反应
4. 可以表现出情绪、压力、疲劳等状态
5. 与其他角色互动时要考虑关系和语境
"""

        if self.personality.system_prompt:
            base_prompt += f"\n【额外设定】\n{self.personality.system_prompt}"

        return base_prompt

    async def speak(self, context: dict, prompt: str | None = None) -> str:
        """
        使用 LLM 生成发言

        Args:
            context: 当前情境信息
            prompt: 可选的外部提示

        Returns:
            发言内容
        """
        self.state = AgentState.SPEAKING
        self._notify_state_change()

        # 构建提示词
        system_prompt = self.get_system_prompt()
        memory_context = self.memory.get_context_summary()

        # 构建情境描述
        situation = f"""【当前情况】
回合: {context.get('turn', 'N/A')}
环境: {context.get('environment', '未知')}

【最近记忆】
{memory_context}
"""

        if prompt:
            situation += f"\n【需要回应】\n{prompt}"

        # 添加关系信息
        relationships = []
        for other_id, relation in self.personality.relationships.items():
            relationships.append(f"- {other_id}: {relation}")
        if relationships:
            situation += f"\n【人际关系】\n{chr(10).join(relationships)}"

        # 添加状态信息
        state_desc = self.get_state_description()
        situation += f"\n【你的状态】\n{state_desc}"

        try:
            # 调用 LLM
            response = await self.llm_client.generate_async(
                prompt=situation,
                system_prompt=system_prompt
            )

            content = response.content.strip()

            # 清理可能的格式标记
            if content.startswith("```"):
                content = content.split("```", 2)[-1].strip()
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            if content.startswith("'") and content.endswith("'"):
                content = content[1:-1]

            # 限制长度
            if len(content) > 200:
                content = content[:197] + "..."

        except Exception as e:
            # 降级到简单响应
            content = await self._fallback_response()

        # 记录
        self.memory.add(
            content=f"我说: {content}",
            source="self",
            importance=0.6,
            tags=["speech", "llm"]
        )

        # 更新对话历史
        self._conversation_history.append(("assistant", content))

        self.state = AgentState.IDLE
        self._notify_state_change()

        return content

    async def _fallback_response(self) -> str:
        """降级响应（LLM 失败时使用）"""
        fallback_responses = {
            AgentRole.LEADER: ["我们需要一个计划。", "让我来处理。"],
            AgentRole.PEACEMAKER: ["大家都冷静一下。", "我们可以商量。"],
            AgentRole.DRAMA_QUEEN: ["这太疯狂了！", "我无法接受！"],
            AgentRole.SLACKER: ["嗯...随便吧。", "你们决定。"],
            AgentRole.PERFECTIONIST: ["这里有问题。", "需要仔细考虑。"],
            AgentRole.WILDCARD: ["等等，我有想法。", "换个思路？"]
        }
        import random
        return random.choice(fallback_responses.get(self.role, ["好吧。"]))

    async def think(self, context: dict) -> str:
        """使用 LLM 进行思考"""
        self.state = AgentState.THINKING
        self._notify_state_change()

        system_prompt = f"""你是 {self.name}，正在思考当前情况。
请用简短的内心独白表达你的想法（不超过 30 字）。
完全代入角色，体现你的性格特征。"""

        situation = f"""【当前情况】
{context.get('environment', '未知')}

【最近的记忆】
{self.memory.get_context_summary()}
"""

        try:
            response = await self.llm_client.generate_async(
                prompt=situation,
                system_prompt=system_prompt
            )
            thought = response.content.strip()
        except Exception:
            thought = "正在观察局势..."

        self.state = AgentState.IDLE
        self._notify_state_change()

        return thought

    def listen(self, speaker_id: str, content: str) -> None:
        """倾听他人发言"""
        self.state = AgentState.LISTENING

        # 记录到对话历史
        self._conversation_history.append((speaker_id, content))

        # 调用父类的 listen 方法
        super().listen(speaker_id, content)

        self.state = AgentState.IDLE


def create_agent(
    name: str,
    role: str | AgentRole,
    use_llm: bool = False,
    llm_provider: str = "gemini",
    **kwargs
) -> Agent:
    """
    便捷函数：创建 Agent

    Args:
        name: Agent 名称
        role: 角色类型
        use_llm: 是否使用 LLM
        llm_provider: LLM 提供商 (gemini, openai, anthropic)
        **kwargs: 其他配置参数

    Returns:
        Agent 实例
    """
    if isinstance(role, str):
        role = AgentRole(role)

    if use_llm:
        return LLMAgent(
            name=name,
            role=role,
            llm_provider=llm_provider,
            **kwargs
        )

    return SimpleAgent(name=name, role=role, **kwargs)
