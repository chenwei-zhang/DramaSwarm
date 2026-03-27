"""
LLM Client Module - LLM 客户端集成

支持多种 LLM 提供商：Gemini, OpenAI, Anthropic 等。
"""

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class Message:
    """消息类"""
    role: str  # system, user, assistant
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(role=data["role"], content=data["content"])


@dataclass
class LLMResponse:
    """LLM 响应类"""
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = ""
    raw_response: Any = None

    def __str__(self) -> str:
        return self.content


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "gemini"  # gemini, openai, anthropic
    model: str = "gemini-2.0-flash-exp"
    api_key: str = ""
    temperature: float = 0.8
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40


class LLMClient(ABC):
    """
    LLM 客户端基类

    定义统一的接口，支持多种 LLM 提供商。
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（同步）"""
        pass

    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（异步）"""
        pass

    def chat(
        self,
        messages: list[Message],
        **kwargs
    ) -> LLMResponse:
        """对话接口"""
        prompt = self._messages_to_prompt(messages)
        system_prompt = None
        if messages and messages[0].role == "system":
            system_prompt = messages[0].content
            messages = messages[1:]
        return self.generate(prompt, system_prompt, messages)

    async def chat_async(
        self,
        messages: list[Message],
        **kwargs
    ) -> LLMResponse:
        """对话接口（异步）"""
        prompt = self._messages_to_prompt(messages)
        system_prompt = None
        if messages and messages[0].role == "system":
            system_prompt = messages[0].content
            messages = messages[1:]
        return await self.generate_async(prompt, system_prompt, messages)

    def _messages_to_prompt(self, messages: list[Message]) -> str:
        """将消息列表转换为提示词"""
        if not messages:
            return ""
        # 返回最后一条用户消息
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        return messages[-1].content


class GeminiClient(LLMClient):
    """
    Gemini 客户端

    使用 Google Genai SDK。
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        try:
            from google import genai
            self.genai = genai

            # 初始化客户端
            api_key = config.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Google API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")

            self.client = geni.Client(api_key=api_key)
        except ImportError:
            raise ImportError(
                "Google Genai SDK not installed. "
                "Run: pip install google-genai"
            )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（同步）"""
        return asyncio.run(self.generate_async(prompt, system_prompt, history))

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（异步）"""
        # 构建内容
        contents = []
        if system_prompt:
            contents.append(f"[系统指令]\n{system_prompt}\n")
        if history:
            for msg in history:
                if msg.role == "user":
                    contents.append(f"[{msg.role}]\n{msg.content}\n")
                elif msg.role == "assistant":
                    contents.append(f"[{msg.role}]\n{msg.content}\n")
        contents.append(f"[user]\n{prompt}\n")

        content_text = "\n".join(contents)

        try:
            # 使用新 API
            response = self.client.models.generate_content(
                model=self.model,
                contents=content_text
            )

            return LLMResponse(
                content=response.text,
                model=self.model,
                raw_response=response
            )
        except Exception as e:
            # 返回错误信息
            return LLMResponse(
                content=f"[LLM 错误] {str(e)}",
                model=self.model
            )


class OpenAIClient(LLMClient):
    """
    OpenAI 客户端

    使用 OpenAI API。
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        try:
            from openai import OpenAI
            api_key = config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found.")

            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. "
                "Run: pip install openai"
            )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（同步）"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            for msg in history:
                messages.append(msg.to_dict())

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            return LLMResponse(
                content=f"[LLM 错误] {str(e)}",
                model=self.model
            )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（异步）"""
        # 简化：同步调用
        return self.generate(prompt, system_prompt, history)


class AnthropicClient(LLMClient):
    """
    Anthropic 客户端

    使用 Anthropic API (Claude)。
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        try:
            from anthropic import Anthropic
            api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key not found.")

            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "Anthropic SDK not installed. "
                "Run: pip install anthropic"
            )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（同步）"""
        messages = []

        if history:
            for msg in history:
                if msg.role != "system":
                    messages.append(msg.to_dict())

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt or "",
                messages=messages
            )

            return LLMResponse(
                content=response.content[0].text,
                model=self.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens
            )
        except Exception as e:
            return LLMResponse(
                content=f"[LLM 错误] {str(e)}",
                model=self.model
            )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[Message] | None = None
    ) -> LLMResponse:
        """生成响应（异步）"""
        return self.generate(prompt, system_prompt, history)


def get_client(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    **kwargs
) -> LLMClient:
    """
    获取 LLM 客户端实例

    Args:
        provider: 提供商 (gemini, openai, anthropic)
        model: 模型名称
        api_key: API 密钥
        **kwargs: 其他配置参数

    Returns:
        LLMClient 实例
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "gemini")

    if model is None:
        model = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")

    config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key or "",
        **kwargs
    )

    client_classes = {
        "gemini": GeminiClient,
        "google": GeminiClient,
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "claude": AnthropicClient,
    }

    client_class = client_classes.get(provider.lower())
    if not client_class:
        raise ValueError(f"Unknown provider: {provider}")

    return client_class(config)


# 便捷函数
def generate(
    prompt: str,
    system_prompt: str | None = None,
    provider: str = "gemini",
    model: str | None = None
) -> str:
    """
    便捷函数：生成响应

    Args:
        prompt: 提示词
        system_prompt: 系统提示词
        provider: LLM 提供商
        model: 模型名称

    Returns:
        生成的文本
    """
    client = get_client(provider=provider, model=model)
    response = client.generate(prompt, system_prompt)
    return response.content


async def generate_async(
    prompt: str,
    system_prompt: str | None = None,
    provider: str = "gemini",
    model: str | None = None
) -> str:
    """
    便捷函数：异步生成响应

    Args:
        prompt: 提示词
        system_prompt: 系统提示词
        provider: LLM 提供商
        model: 模型名称

    Returns:
        生成的文本
    """
    client = get_client(provider=provider, model=model)
    response = await client.generate_async(prompt, system_prompt)
    return response.content
