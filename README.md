# SwarmSim - 多智能体群体仿真引擎

> 基于 MiroFish 概念的垂直领域实现：**综艺节目修罗场/CP感推演器**

## 项目简介

SwarmSim 是一个轻量级的多智能体仿真引擎，专注于模拟复杂社交场景中的群体行为。本项目采用**垂直切入**策略，首先实现综艺节目场景的推演能力。

### 核心特性

- **Agent 生成器**: 从种子信息自动生成具有独立人格的智能体
- **环境模块**: 维护全局时间线、环境变量和事件流
- **事件驱动引擎**: 控制智能体交互的节拍和状态流转
- **观测总结模块**: 实时分析群体动态并生成推演报告

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key

创建 `.env` 文件：

```bash
# OpenAI API (可选)
OPENAI_API_KEY=your_key_here

# Anthropic API (可选)
ANTHROPIC_API_KEY=your_key_here

# 默认使用模型
DEFAULT_MODEL=gpt-4o-mini
```

### 运行 Demo

```bash
# 综艺节目修罗场模拟
python -m demos.variety_show_simulation
```

## 项目结构

```
swarmsim/
├── core/
│   ├── agent.py          # Agent 基类与核心逻辑
│   ├── environment.py    # 环境模块
│   ├── event_loop.py     # 事件驱动引擎
│   ├── factory.py        # Agent 工厂
│   └── observer.py       # 观测总结模块
├── memory/
│   ├── base.py           # 记忆基类
│   └── vector_store.py   # 向量存储
├── prompts/
│   └── personas.yaml     # 人设模板
├── demos/
│   └── variety_show_simulation.py
└── tests/
    └── test_agent.py
```

## 开发路线图

- [x] Phase 1: 基础框架 - 3-5 个 Agent 的简单对话
- [ ] Phase 2: 扩展规模 - 支持 50+ Agent 并行交互
- [ ] Phase 3: 引入知识图谱 - 基于 GraphRAG 的关系管理
- [ ] Phase 4: 垂直场景 - 综艺节目推演完整功能

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                   Observer Agent                     │
│              (群体分析 & 报告生成)                    │
└────────────────────┬────────────────────────────────┘
                     │ 监控所有交互
┌────────────────────▼────────────────────────────────┐
│              Environment (上帝环境)                   │
│    时间线 | 天气 | 全局事件 | 广播公告板             │
└─────┬───────────────┬───────────────────┬───────────┘
      │               │                   │
┌─────▼─────┐   ┌────▼────┐      ┌──────▼──────┐
│  Agent A  │   │ Agent B │      │  Agent N    │
│  人设+记忆 │   │ 人设+记忆│      │  人设+记忆   │
└───────────┘   └─────────┘      └─────────────┘
      │               │                   │
      └───────────────┴───────────────────┘
                     │
            ┌────────▼────────┐
            │   Event Loop    │
            │  (事件驱动引擎)  │
            └─────────────────┘
```

## 许可证

MIT License
