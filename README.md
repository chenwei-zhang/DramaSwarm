# DramaSwarm - 多智能体群体仿真引擎

> 基于 MiroFish 概念的垂直领域实现：**综艺节目修罗场/CP感推演器**

## 项目简介

DramaSwarm 是一个轻量级的多智能体仿真引擎，专注于模拟复杂社交场景中的群体行为。本项目采用**垂直切入**策略，首先实现综艺节目场景的推演能力。

### 核心特性

- **Agent 生成器**: 从种子信息自动生成具有独立人格的智能体
- **多层反应系统**: 事件触发公众舆论→媒体报道→热搜发酵→政府监管→品牌解约的连锁反应
- **事件驱动引擎**: 控制智能体交互的节拍和状态流转
- **观测总结模块**: 实时分析群体动态并生成推演报告
- **GraphRAG 可视化**: Web 界面交互式探索知识图谱，D3.js 力导向图展示明星关系网络

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key

创建 `.env` 文件：

```bash
# Gemini API（主要使用）
GEMINI_API_KEY=your_key_here

# 默认使用模型
LLM_MODEL=gemini-3-flash-preview

# 仿真参数
MAX_AGENTS=50
SIMULATION_TICK_INTERVAL=1.0
MEMORY_RETENTION_TURNS=10
DEFAULT_TURNS=50
```

### 运行 Demo

```bash
# 综艺节目修罗场模拟
python -m demos.variety_show_simulation

# 知识图谱可视化（Web 界面）
python run_viz.py
# 浏览器打开 http://localhost:8765

# 知识图谱交互式探索（CLI）
python explore_graph.py
python explore_graph.py 杨幂
python explore_graph.py path 杨幂 PG One

# 明星数据爬虫（模拟模式）
python test_scraper.py mock 杨幂

# 明星数据爬虫（真实爬取）
python test_scraper.py real 杨幂
```

## 项目结构

```
DramaSwarm/
├── .env                          # 环境变量配置
├── .env.example                  # 环境变量示例
├── requirements.txt              # Python 依赖
├── prompt.txt                    # 项目需求文档
├── test_scraper.py               # 爬虫测试脚本
│
├── swarmsim/                     # 多智能体仿真引擎
│   ├── core/
│   │   ├── agent.py              # Agent 基类与 LLM Agent
│   │   ├── environment/          # 环境模块（包）
│   │   │   ├── __init__.py       # 统一导出
│   │   │   ├── base.py           # Environment 基类
│   │   │   ├── variety_show.py   # 综艺节目专用环境
│   │   │   ├── models.py         # 反应系统数据模型
│   │   │   ├── reaction_bus.py   # 反应协调器
│   │   │   └── layers/           # 五大反应层
│   │   │       ├── public_opinion.py  # 公众舆论/粉丝反应
│   │   │       ├── media.py           # 媒体报道/标题生成
│   │   │       ├── social_platform.py # 社交平台/热搜榜
│   │   │       ├── government.py      # 政府监管/关键词审查
│   │   │       └── commercial.py      # 商业品牌/代言解约
│   │   ├── event_loop.py         # 事件驱动引擎
│   │   ├── factory.py            # Agent 工厂
│   │   └── observer.py           # 观测总结模块
│   ├── graph/                   # 知识图谱模块（GraphRAG）
│   │   └── knowledge_graph.py   # networkx 图引擎 + 查询 + 上下文生成
│   ├── viz/                     # 可视化模块（FastAPI + D3.js）
│   │   ├── server.py            # FastAPI 应用
│   │   ├── api_graph.py         # 图谱 API 路由
│   │   ├── api_simulation.py    # 仿真 API 路由
│   │   └── serializer.py        # networkx → D3 JSON 转换
│   ├── static/
│   │   └── index.html           # D3.js 力导向图可视化页面
│   ├── llm/
│   │   └── client.py             # LLM 客户端（Gemini/OpenAI/Anthropic）
│   └── memory/
│       └── base.py               # 记忆基类
│
├── celebrity_scraper/            # 明星数据爬虫
│   ├── scraper.py                # 爬虫主调度器
│   ├── models.py                 # 数据模型定义
│   ├── mock_data.py              # 模拟数据生成器
│   ├── spiders/
│   │   ├── baidu_baike.py        # 百度百科
│   │   ├── weibo.py              # 微博
│   │   ├── zhihu.py              # 知乎
│   │   ├── douban.py             # 豆瓣
│   │   └── news.py               # 娱乐新闻聚合
│   ├── utils/
│   │   └── anti_spider.py        # 反爬虫工具
│   └── data/                     # 爬取数据（JSON）
│       ├── 肖战.json
│       ├── 杨幂.json
│       ├── 李小璐.json
│       ├── summary.json
│       └── ...
│
├── demos/
│   └── variety_show_simulation.py # 综艺修罗场模拟 Demo
│
└── tests/
    └── test_agent.py             # 单元测试
```

## 开发路线图

- [x] Phase 1: 基础框架 - 3-5 个 Agent 的简单对话
- [x] Phase 2: 多层反应系统 - 公众舆论/媒体/热搜/监管/品牌五层链式反应
- [x] Phase 3: 知识图谱 - 基于 GraphRAG 的关系管理与图推理上下文注入
- [ ] Phase 4: 扩展规模 - 支持 50+ Agent 并行交互
- [ ] Phase 5: 垂直场景 - 综艺节目推演完整功能

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Observer Agent                          │
│                 (群体分析 & 报告生成)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ 监控所有交互
┌──────────────────────────▼──────────────────────────────────┐
│                  Environment (上帝环境)                       │
│        时间线 | 天气 | 全局事件 | 广播公告板                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               ReactionBus 反应协调器                  │   │
│  │                                                      │   │
│  │  事件 ──→ ① PublicOpinionLayer  (公众舆论/好感度)     │   │
│  │          ② MediaLayer           (媒体报道/标题生成)   │   │
│  │          ③ SocialPlatformLayer  (热搜榜/曝光量)       │   │
│  │          ④ GovernmentLayer      (关键词审查/封禁)     │   │
│  │          ⑤ CommercialLayer      (品牌代言/商业价值)   │   │
│  │                                                      │   │
│  │  ──→ 反馈到 Agent.perceive() 影响后续行为             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           KnowledgeGraph 知识图谱 (GraphRAG)          │   │
│  │   celebrity_scraper/data/*.json → networkx 图         │   │
│  │   节点: Celebrity / GossipEvent / News                │   │
│  │   边: relationship / involved_in / simulation_event    │   │
│  │   → 查询关系上下文 / 事件影响 / 最短路径推理            │   │
│  │   → 注入 Agent.perceive() 的 graph_context             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────┬───────────────┬───────────────────┬──────────────────┘
      │               │                   │
┌─────▼─────┐   ┌────▼────┐      ┌──────▼──────┐
│  Agent A  │   │ Agent B │      │  Agent N    │
│  人设+记忆 │   │ 人设+记忆│      │  人设+记忆   │
│ +图谱上下文│   │+图谱上下文│      │ +图谱上下文  │
└───────────┘   └─────────┘      └─────────────┘
      │               │                   │
      └───────────────┴───────────────────┘
                     │
            ┌────────▼────────┐
            │   Event Loop    │
            │  (事件驱动引擎)  │
            └────────┬────────┘
                     │
       ┌─────────────▼──────────────┐
       │   FastAPI Visualization     │
       │   ┌─────────────────────┐  │
       │   │  D3.js 力导向图     │  │
       │   │  明星关系 · 八卦事件 │  │
       │   │  路径查找 · 仿真仪表 │  │
       │   └─────────────────────┘  │
       │   GET /api/graph/*         │
       │   GET /api/sim/*           │
       └────────────────────────────┘
```

## 许可证

MIT License
