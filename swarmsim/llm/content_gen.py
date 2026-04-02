# -*- coding: utf-8 -*-
"""
内容生成器 — 统一的文本内容生成层

支持三种模式：
  - template: 纯模板模式（默认，无需 API key）
  - llm: 强制 LLM 模式
  - auto: LLM 优先，失败自动回退模板（推荐）

各模块（谣言、评论、头条等）不再直接使用硬编码模板，
而是通过 ContentGenerator 获取内容，透明切换模板/LLM。
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
import asyncio
from abc import ABC, abstractmethod
from typing import Any

from swarmsim.llm.client import LLMClient, get_client

logger = logging.getLogger(__name__)


class ContentGenerator(ABC):
    """内容生成器基类"""

    @abstractmethod
    def generate(self, context: dict[str, Any]) -> str:
        """同步生成内容"""
        ...

    @abstractmethod
    async def generate_async(self, context: dict[str, Any]) -> str:
        """异步生成内容"""
        ...

    def generate_batch(self, contexts: list[dict[str, Any]]) -> list[str]:
        """批量生成（默认逐条调用）"""
        return [self.generate(ctx) for ctx in contexts]

    async def generate_batch_async(self, contexts: list[dict[str, Any]]) -> list[str]:
        """异步批量生成"""
        return [await self.generate_async(ctx) for ctx in contexts]


class TemplateContentGenerator(ContentGenerator):
    """从模板列表中随机选择并格式化"""

    def __init__(self, templates: list[str] | dict[str, list[str]], name: str = ""):
        self.name = name
        if isinstance(templates, dict):
            # 扁平化所有分组
            self._templates: list[str] = []
            for group in templates.values():
                if isinstance(group, list):
                    self._templates.extend(group)
                else:
                    self._templates.append(str(group))
        else:
            self._templates = list(templates)

        if not self._templates:
            self._templates = ["{actor}做出了回应"]

    def generate(self, context: dict[str, Any]) -> str:
        template = random.choice(self._templates)
        try:
            return template.format(**{k: v for k, v in context.items() if isinstance(v, (str, int, float))})
        except (KeyError, IndexError):
            return template

    async def generate_async(self, context: dict[str, Any]) -> str:
        return self.generate(context)


class LLMContentGenerator(ContentGenerator):
    """基于 LLM 的内容生成器，含缓存和超时"""

    def __init__(
        self,
        name: str,
        templates: list[str] | dict[str, list[str]],
        llm_client: LLMClient,
        prompt_builder: Any | None = None,
        max_tokens: int = 256,
        temperature: float = 0.9,
    ):
        self.name = name
        self.llm_client = llm_client
        self.template_gen = TemplateContentGenerator(templates, name)
        self.prompt_builder = prompt_builder
        self.max_tokens = max_tokens
        self.temperature = temperature
        # 内存缓存: hash_key -> generated_text
        self._cache: dict[str, str] = {}
        self._max_cache = 500

    def _cache_key(self, context: dict[str, Any]) -> str:
        raw = f"{self.name}:{sorted(context.items())}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _build_prompt(self, context: dict[str, Any]) -> tuple[str, str]:
        """构建 (system_prompt, user_prompt)"""
        if self.prompt_builder:
            return self.prompt_builder(context)

        # 通用默认 prompt
        content_type = context.get("content_type", self.name)
        system_prompt = f"你是一个{content_type}内容生成器。只输出内容文本，不要解释。"
        user_parts = []
        for k, v in context.items():
            if k != "content_type" and isinstance(v, (str, int, float)):
                user_parts.append(f"{k}：{v}")
        user_prompt = "\n".join(user_parts) + "\n请生成内容。"
        return system_prompt, user_prompt

    def _validate_result(self, text: str) -> bool:
        """校验 LLM 输出"""
        if not text or not text.strip():
            return False
        if "[LLM 错误]" in text:
            return False
        if len(text) > 500:
            return False
        return True

    def generate(self, context: dict[str, Any]) -> str:
        key = self._cache_key(context)
        if key in self._cache:
            return self._cache[key]

        system_prompt, user_prompt = self._build_prompt(context)
        try:
            response = self.llm_client.generate(user_prompt, system_prompt=system_prompt)
            text = response.content.strip()
            if self._validate_result(text):
                if len(self._cache) >= self._max_cache:
                    # 简单淘汰：清空一半
                    keys = list(self._cache.keys())
                    for k in keys[:len(keys)//2]:
                        del self._cache[k]
                self._cache[key] = text
                return text
            else:
                logger.warning(f"[ContentGen:{self.name}] LLM 输出无效，回退模板")
                return self.template_gen.generate(context)
        except Exception as e:
            logger.warning(f"[ContentGen:{self.name}] LLM 调用失败: {e}，回退模板")
            return self.template_gen.generate(context)

    async def generate_async(self, context: dict[str, Any]) -> str:
        key = self._cache_key(context)
        if key in self._cache:
            return self._cache[key]

        system_prompt, user_prompt = self._build_prompt(context)
        try:
            response = await asyncio.wait_for(
                self.llm_client.generate_async(user_prompt, system_prompt=system_prompt),
                timeout=15.0,
            )
            text = response.content.strip()
            if self._validate_result(text):
                if len(self._cache) >= self._max_cache:
                    keys = list(self._cache.keys())
                    for k in keys[:len(keys)//2]:
                        del self._cache[k]
                self._cache[key] = text
                return text
            else:
                logger.warning(f"[ContentGen:{self.name}] LLM 输出无效，回退模板")
                return await self.template_gen.generate_async(context)
        except asyncio.TimeoutError:
            logger.warning(f"[ContentGen:{self.name}] LLM 超时(15s)，回退模板")
            return self.template_gen.generate(context)
        except Exception as e:
            logger.warning(f"[ContentGen:{self.name}] LLM 调用失败: {e}，回退模板")
            return self.template_gen.generate(context)


class FallbackContentGenerator(ContentGenerator):
    """LLM 优先，失败自动回退模板"""

    def __init__(self, llm_gen: LLMContentGenerator, template_gen: TemplateContentGenerator):
        self.llm_gen = llm_gen
        self.template_gen = template_gen

    def generate(self, context: dict[str, Any]) -> str:
        return self.llm_gen.generate(context)

    async def generate_async(self, context: dict[str, Any]) -> str:
        return await self.llm_gen.generate_async(context)


# ── Prompt Builder 工厂 ──

def _build_rumor_prompt(context: dict[str, Any]) -> tuple[str, str]:
    """谣言生成 prompt — 基于具体事件上下文"""
    gossip_labels = {
        "cheating": "出轨", "scandal": "丑闻", "divorce": "离婚",
        "drugs": "涉毒", "tax_evasion": "偷税漏税", "other": "负面",
    }
    gossip_type = context.get("gossip_type", "other")
    person = context.get("person", "某明星")
    target = context.get("target", "相关人员")
    days_silent = context.get("days_silent", 2)
    severity = context.get("severity", 0.3)
    scenario_desc = context.get("scenario_description", "")
    scenario_title = context.get("scenario_title", "")

    severity_desc = "轻微" if severity < 0.4 else "中等" if severity < 0.6 else "严重" if severity < 0.8 else "极其离谱"

    system = (
        "你是娱乐八卦爆料号写手。根据具体的危机事件，生成一条听起来像微博匿名爆料的传闻（20-50字）。\n"
        "谣言必须围绕该事件本身展开，编造该事件的升级版、内幕、隐瞒细节或牵连他人。\n"
        "不要编造与该事件无关的内容（如家庭纠纷、个人感情等）。\n"
        "必须包含「据知情人透露」或「网友扒出」或「有爆料称」或「圈内消息称」等话术中的一种。\n"
        "只输出爆料文本，不要解释，不要加引号。"
    )

    event_info = ""
    if scenario_title:
        event_info += f"事件名称：{scenario_title}\n"
    if scenario_desc:
        # 截取前200字避免 prompt 过长
        event_info += f"事件详情：{scenario_desc[:200]}\n"

    user = (
        f"{event_info}"
        f"事件类型：{gossip_labels.get(gossip_type, '负面')}事件\n"
        f"沉默的当事人：{person}（已连续{days_silent}天未回应）\n"
        f"其他涉事人：{target}\n"
        f"沉默越久，传闻越离谱。当前离谱程度：{severity_desc}\n"
        f"请生成一条围绕上述事件本身的网络传闻。"
    )
    return system, user


def _build_comment_prompt(context: dict[str, Any]) -> tuple[str, str]:
    """观众评论批量生成 prompt"""
    persona_type = context.get("persona_type", "路人")
    action_label = context.get("action_label", "回应")
    actor = context.get("actor", "某明星")
    n = context.get("count", 5)
    gossip_type = context.get("gossip_type", "scandal")
    day = context.get("day", 1)
    approval = context.get("approval", 50)

    persona_desc = {
        "粉丝": "无条件支持偶像，为偶像辩护，情绪化",
        "路人": "吃瓜心态，不站队，理性观望",
        "理中客": "冷静分析，提出质疑，强调证据",
        "黑粉": "嘲讽、攻击、要求封杀",
    }.get(persona_type, "普通网友")

    system = (
        f'模拟社交媒体上{persona_type}对明星公关动作的评论。\n'
        f'用户特征：{persona_desc}\n'
        f'生成{n}条评论，每条独立一行。用{actor}代表明星名。\n'
        f'只输出评论，不要编号、不要解释。'
    )
    user = (
        f"明星：{actor}\n"
        f"动作：{action_label}\n"
        f"事件类型：{gossip_type}事件\n"
        f"第{day}天，口碑{approval}/100\n"
        f"生成{n}条微博评论。"
    )
    return system, user


def _build_headline_trending_prompt(context: dict[str, Any]) -> tuple[str, str]:
    """媒体头条 + 热搜话题合并 prompt"""
    phase_label = context.get("phase_label", "危机")
    persons = context.get("persons", "某明星")
    actions_summary = context.get("actions_summary", "无动作")
    heat = context.get("heat", 50)

    system = (
        "你是微博热搜和娱乐新闻模拟器。根据危机进展生成热搜话题和新闻标题。\n"
        "严格按以下格式输出，不要加解释：\n"
        "【热搜】\n"
        "#话题1\n"
        "#话题2\n"
        "#话题3\n"
        "【媒体】\n"
        "媒体名|标题1\n"
        "媒体名|标题2\n"
        "媒体名|标题3\n"
    )
    user = (
        f"危机阶段：{phase_label}\n"
        f"涉及人物：{persons}\n"
        f"当日动作：{actions_summary}\n"
        f"热度指数：{heat}/100\n"
        f"请生成热搜话题和新闻标题。"
    )
    return system, user


# ── 工厂函数 ──

_PROMPT_BUILDERS: dict[str, Any] = {
    "rumor": _build_rumor_prompt,
    "audience_comment": _build_comment_prompt,
    "headline": _build_headline_trending_prompt,
    "trending": _build_headline_trending_prompt,
}


def get_content_generator(
    content_type: str,
    templates: list[str] | dict[str, list[str]],
    llm_client: LLMClient | None = None,
    mode: str | None = None,
) -> ContentGenerator:
    """创建内容生成器

    Args:
        content_type: 内容类型 (rumor/audience_comment/headline/trending)
        templates: 模板字典或列表（用作 fallback）
        llm_client: LLM 客户端（None 时强制模板模式）
        mode: 生成模式 (template/llm/auto)，None 时读环境变量
    """
    mode = mode or os.getenv("CONTENT_GEN_MODE", "template")

    if mode == "template" or llm_client is None:
        return TemplateContentGenerator(templates, name=content_type)
    else:
        prompt_builder = _PROMPT_BUILDERS.get(content_type)
        llm_gen = LLMContentGenerator(
            name=content_type,
            templates=templates,
            llm_client=llm_client,
            prompt_builder=prompt_builder,
        )
        if mode == "auto":
            template_gen = TemplateContentGenerator(templates, name=content_type)
            return FallbackContentGenerator(llm_gen, template_gen)
        else:  # "llm" mode
            return llm_gen
