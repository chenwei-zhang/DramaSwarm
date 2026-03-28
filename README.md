# DramaSwarm - 多智能体群体仿真引擎

> 基于 MiroFish 概念的垂直领域实现：**综艺节目修罗场/CP感推演器**

## 项目简介

DramaSwarm 是一个轻量级的多智能体仿真引擎，专注于模拟复杂社交场景中的群体行为。本项目采用**垂直切入**策略，首先实现综艺节目场景的推演能力，并支持**公关危机 what-if 仿真**。

### 核心特性

- **Agent 生成器**: 从种子信息自动生成具有独立人格的智能体
- **多层反应系统**: 事件触发公众舆论→媒体报道→热搜发酵→政府监管→品牌解约的连锁反应
- **事件驱动引擎**: 控制智能体交互的节拍和状态流转
- **观测总结模块**: 实时分析群体动态并生成推演报告
- **GraphRAG 可视化**: Web 界面交互式探索知识图谱，D3.js 力导向图展示明星关系网络
- **危机仿真引擎**: 基于时序 GraphRAG 的多 Agent 公关危机模拟，支持 what-if 干预和结果对比分析
- **多 Agent 交互**: 顺序决策 + 关系影响 + 观众反应 + 社交传播，Agent 之间有真实互动

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

# 危机仿真（纯规则模式，无需 API key）
python -m demos.crisis_simulation

# 知识图谱可视化（Web 界面，含危机模拟 Tab）
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
│   │   ├── knowledge_graph.py   # networkx 图引擎 + 查询 + 上下文生成
│   │   └── temporal.py          # 时序 GraphRAG（日期索引 + 人物时间线）
│   ├── crisis/                  # 危机仿真引擎
│   │   ├── models.py            # 数据模型（CrisisPhase, PRAction, CrisisState, AgentMessage 等）
│   │   ├── timeline.py          # 时间线（1天=1回合，6阶段危机生命周期）
│   │   ├── action_space.py      # 10种 PR 策略效果矩阵 + 阶段/性格修正
│   │   ├── persona_agent.py     # 明星 Agent（规则/LLM 双模式，Big Five 人设，支持交互）
│   │   ├── vacuum_detector.py   # 信息真空→谣言级联检测
│   │   ├── intervention.py      # 用户 what-if 干预系统
│   │   ├── message_bus.py       # Agent 间消息总线
│   │   ├── audience.py          # 观众池（粉丝/路人/理中客/黑粉，模板评论）
│   │   ├── scenario_engine.py   # 仿真引擎核心（场景加载 + 顺序决策 + 异步仿真循环）
│   │   └── outcome_analyzer.py  # 仿真 vs 历史基线对比分析
│   ├── viz/                     # 可视化模块（FastAPI + D3.js）
│   │   ├── server.py            # FastAPI 应用
│   │   ├── api_graph.py         # 图谱 API 路由
│   │   ├── api_simulation.py    # 仿真 API 路由
│   │   ├── api_crisis.py        # 危机仿真 API（10个端点）
│   │   └── serializer.py        # networkx → D3 JSON 转换
│   ├── static/
│   │   └── index.html           # Web 可视化（知识图谱 + 危机模拟 Tab）
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
│   ├── variety_show_simulation.py # 综艺修罗场模拟 Demo
│   └── crisis_simulation.py      # 危机仿真 CLI Demo（纯规则模式）
│
└── tests/
    ├── test_agent.py             # Agent 单元测试
    ├── test_temporal_graph.py    # 时序图谱测试
    └── test_crisis_engine.py     # 危机引擎测试
```

## 开发路线图

- [x] Phase 1: 基础框架 - 3-5 个 Agent 的简单对话
- [x] Phase 2: 多层反应系统 - 公众舆论/媒体/热搜/监管/品牌五层链式反应
- [x] Phase 3: 知识图谱 - 基于 GraphRAG 的关系管理与图推理上下文注入
- [x] Phase 4: 危机仿真引擎 - 时序 GraphRAG + 多 Agent 公关危机模拟 + what-if 干预 + 结果对比
- [ ] Phase 5: 扩展规模 - 支持 50+ Agent 并行交互
- [ ] Phase 6: 垂直场景 - 综艺节目推演完整功能

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
│  │      TemporalKnowledgeGraph 时序知识图谱               │   │
│  │   celebrity_scraper/data/*.json → networkx 图         │   │
│  │   节点: Celebrity / GossipEvent / News                │   │
│  │   边: relationship / involved_in / simulation_event    │   │
│  │   → 日期索引 + 人物时间线 + 危机场景提取                 │   │
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
       │   │  知识图谱 Tab        │  │
       │   │  D3.js 力导向图     │  │
       │   │  明星关系 · 八卦事件 │  │
       │   │  路径查找 · 仿真仪表 │  │
       │   ├─────────────────────┤  │
       │   │  危机模拟 Tab        │  │
       │   │  口碑走势 · 热搜榜  │  │
       │   │  观众反应 · 媒体头条 │  │
       │   │  品牌状态 · 交互日志 │  │
       │   │  干预面板 · 结果对比 │  │
       │   └─────────────────────┘  │
       │   /api/graph/*             │
       │   /api/sim/*               │
       │   /api/crisis/*            │
       └────────────────────────────┘
```

## 危机仿真引擎

基于时序 GraphRAG 的多 Agent 公关危机模拟系统，支持 what-if 场景推演。

### 仿真流程

```
用户选择场景 → CrisisScenarioEngine 从图谱加载 → CrisisSimulation 运行
                                                     │
每回合（1天）:                                        │
  1. CrisisTimeline.advance_day() → 确定危机阶段      │
  2. InterventionSystem.check() → 应用用户干预         │
  3. 顺序决策：Agent 依次行动                           │
     └→ 后决策者看到前面人的动作 + 观众反应             │
     └→ 关系影响：配偶道歉→自己也缓和，对手反击→强硬    │
     └→ 传播效应：亲密关系者重大动作触发额外响应         │
  4. AudiencePool → 30个观众Agent生成评论               │
  5. InformationVacuumDetector → 沉默触发谣言          │
  6. CrisisActionSpace.compute_effect() → 计算效果     │
  7. 热搜/媒体/品牌/监管 状态更新                       │
  8. 自然衰减（热度-10%/天，口碑回归50）                │
                                                     │
30天后 → OutcomeAnalyzer 对比仿真 vs 历史基线          │
```

### 危机生命周期

| 阶段 | 天数 | 特点 |
|------|------|------|
| 爆发期 | Day 1 | 事件刚曝光，慌乱应对 |
| 发酵期 | Day 2-3 | 细节流出，舆论升级 |
| 高峰期 | Day 4-7 | 全网讨论，最佳回应窗口 |
| 应对期 | Day 8-14 | 公关策略见效/失效 |
| 收尾期 | Day 15-21 | 降温，公益/复出可行 |
| 余波期 | Day 22+ | 长期影响，事业转型 |

### 10种公关策略

沉默、道歉、声明、上节目、起诉、卖惨、反击、隐退、公益、复出。每种策略在不同阶段有不同效果系数（如高峰期道歉效果×1.2，爆发期上节目仅×0.2）。

### 多 Agent 交互机制

- **顺序决策**：明星 Agent 按顺序行动，后决策者感知前面人的动作并受其影响
- **关系影响**：基于知识图谱中的关系类型（配偶/对手/搭档等），对方的动作会调整自己的决策权重
  - 配偶道歉 → 自己也倾向缓和（道歉/声明加权 +1.5）
  - 对手反击 → 自己也倾向强硬（反击加权 +1.5）
  - 被指名 → 必须回应（声明加权 +2.0）
- **观众反应**：30 个观众 Agent（粉丝 40%/路人 30%/理中客 20%/黑粉 10%）基于模板生成评论，明星感知观众情绪后调整策略
- **社交传播**：亲密关系者做了重大动作（道歉/反击/卖惨）→ 触发额外响应标记

## 许可证

MIT License
