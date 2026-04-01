# DramaSwarm - 娱乐圈危机公关仿真引擎

> 基于多智能体仿真的**娱乐圈危机公关推演器**

## 项目简介

DramaSwarm 是一个轻量级的多智能体仿真引擎，专注于模拟娱乐圈公关危机场景中的群体行为。基于时序知识图谱（GraphRAG）构建明星关系网络，运行多 Agent 危机仿真，支持 **what-if 干预推演**和**对照实验**。

### 核心特性

- **危机仿真引擎**: 基于时序 GraphRAG 的多 Agent 公关危机模拟，支持 what-if 干预和结果对比分析
- **角色感知决策**: Agent 自动推断危机角色（加害者/受害者/第三者），决策策略与角色匹配（出轨者不复出、受害者不道歉）
- **多 Agent 交互**: 顺序决策 + 关系影响 + 观众反应 + 社交传播，Agent 之间有真实互动
- **深度人格建模**: 10 维确定性人格画像，从 10+ 类图谱数据源（职业/Bio/粉丝/作品/公司/历史事件/关系网/年龄/正面新闻/二度连接/关系强度）自动构建
- **结构化记忆系统**: Agent 拥有 MemoryStore 驱动的长期记忆，支持重要性排序、遗忘曲线、语义搜索，记忆影响决策
- **八卦类型感知**: 出轨/涉毒/偷税/离婚/丑闻等不同危机类型自动调整策略（涉毒禁反击、离婚倾向声明）
- **观众记忆驱动**: 观众 Agent 记录评论历史，重复动作降低评论概率，语义相似动作共享惩罚
- **GraphRAG 可视化**: Web 界面交互式探索知识图谱，D3.js 力导向图展示明星关系网络
- **自由组局**: 自定义场景 + 明星选择 + 关系定义，支持危机模式和自由互动模式
- **丰富干预**: 三类触发（定时/相对天数/状态阈值）+ 三类动作（强制PR/外部事件/关系变更）
- **对照实验**: 同一场景多组干预配置并行仿真，自动对比口碑差值并推荐最佳策略

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

# 运行全部测试（102 个测试）
pytest tests/ -v
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
│   ├── graph/                   # 知识图谱模块（GraphRAG）
│   │   ├── knowledge_graph.py   # networkx 图引擎 + 查询 + 上下文生成
│   │   └── temporal.py          # 时序 GraphRAG（日期索引 + 人物时间线）
│   ├── crisis/                  # 危机仿真引擎
│   │   ├── models.py            # 数据模型（CrisisPhase, PRAction, CrisisRole, CrisisState, AgentMessage 等）
│   │   ├── timeline.py          # 时间线（1天=1回合，6阶段危机生命周期）
│   │   ├── action_space.py      # 10种 PR 策略效果矩阵 + 阶段/性格修正
│   │   ├── persona_agent.py     # 明星 Agent（规则/LLM 双模式，Big Five 人设，支持交互）
│   │   ├── vacuum_detector.py   # 信息真空→谣言级联检测
│   │   ├── intervention.py      # 用户 what-if 干预系统
│   │   ├── message_bus.py       # Agent 间消息总线
│   │   ├── audience.py          # 观众池（粉丝/路人/理中客/黑粉，模板评论）
│   │   ├── scenario_engine.py   # 仿真引擎核心（场景加载 + 自定义组局 + 顺序决策 + 自由/危机双模式）
│   │   ├── experiment.py        # A/B 对照实验（ExperimentManager + 多组对比）
│   │   └── outcome_analyzer.py  # 仿真 vs 历史基线对比分析
│   ├── viz/                     # 可视化模块（FastAPI + D3.js）
│   │   ├── server.py            # FastAPI 应用
│   │   ├── api_graph.py         # 图谱 API 路由
│   │   ├── api_crisis.py        # 危机仿真 API（场景/自定义/实验等端点）
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
│   └── crisis_simulation.py      # 危机仿真 CLI Demo（纯规则模式）
│
└── tests/
    ├── test_temporal_graph.py    # 时序图谱测试
    ├── test_crisis_engine.py     # 危机引擎测试
    ├── test_persona_agent.py     # 明星 Agent 测试（性格/决策/关系/观众/记忆/传播/gossip_type）
    ├── test_audience.py          # 观众系统测试（偏好/反应/记忆/比例分布）
    ├── test_experiment.py        # 对照实验测试
    └── test_memory_store.py      # 记忆系统测试（CRUD/重要性/遗忘曲线）
```

## 五大增强特性

### Phase 1: 深度人格建模

确定性人格推断系统，从 8 类 GraphRAG 数据源提取 **10 维人格画像**，替代原有 5 维 Big Five：

| 维度 | 数据来源 |
|------|---------|
| openness, conscientiousness, extraversion, agreeableness, neuroticism | 职业、Bio 关键词、历史事件、关系网络 |
| public_visibility | 粉丝量（微博 followers 分级） |
| career_stage | 作品数量 |
| media_savvy | 公司类型（工作室/经纪公司/独立） |
| controversy_history | 历史八卦事件数量 + 重要性加权 |
| risk_tolerance | 从 neuroticism/extraversion/openness/agreeableness 联合推导 |

使用确定性哈希（`name + counter → MD5`）保证同一明星每次仿真人格一致，无需 random seed。新增维度直接影响规则决策权重：高 public_visibility 降低沉默权重，高 media_savvy 加权声明/上节目，高 controversy_history + 低 neuroticism 则倾向谨慎策略。

### Phase 2: 自由组局

支持用户自定义场景，从知识图谱中任选明星组成任意关系网络：

- `CrisisScenarioEngine.create_custom_scenario()` — 自定义标题、描述、参与者、关系定义
- `CrisisScenario.is_custom = True` 标记用户创建的场景
- `InteractionMode` 枚举区分 `CRISIS`（6 阶段危机）和 `FREE`（自由互动）两种模式
- Web API `POST /api/crisis/custom-scenario` 支持前端组局

### Phase 3: 丰富干预维度

干预系统从"定时强制动作"扩展为三类触发 + 三类动作：

**触发类型** (`TriggerType`)：
- `TIME_ABSOLUTE` — 第 X 天触发
- `TIME_RELATIVE` — 仿真开始后 N 天触发
- `STATE_THRESHOLD` — 指标达到阈值时触发（approval / heat / brand / regulatory）

**动作类型** (`InterventionCondition`)：
- 强制 PR 动作 — 指定某人在触发时执行特定策略
- 注入外部事件 — 6 种预设事件类型（媒体报道/视频泄露/对手声明/监管行动/品牌决策/自定义），各自带 approval/heat/brand 效果系数
- 关系变更 — strengthen / weaken / break / new，动态修改图谱中的关系强度

### Phase 4: 多样交互模式

新增 `FreeAction` 枚举（11 种动作）和 `FreeActionSpace`，支持非危机场景的自由互动仿真：

| 动作 | 说明 |
|------|------|
| SPEAK | 公开发言/表态 |
| SUPPORT | 支持/声援某人 |
| CRITICIZE | 批评/抨击某人 |
| COLLABORATE | 合作/联名 |
| SOCIALIZE | 社交/聚餐 |
| ANNOUNCE | 宣布/公布消息 |
| IGNORE | 无视/冷处理 |
| PRIVATE_MSG | 私信/私下沟通 |
| MEDIATE | 调停/撮合 |
| RUMOR | 传谣/散布消息 |
| RETREAT | 收缩/低调回避 |

`CelebrityPersonaAgent.generate_free_response()` 基于性格 + 关系 + 观众情绪加权随机选择动作，`CrisisSimulation.step()` 根据 `InteractionMode` 自动切换决策路径。自由模式下不使用 6 阶段时间线，仅做逐日推演。

### Phase 5: 对照实验

`ExperimentManager` 支持同一场景多组不同干预配置的并行对比实验：

- `Experiment` → 多个 `ExperimentGroup`（每组独立干预列表）
- `ExperimentManager.run_experiment()` — 依次运行每组仿真，收集 history + final_state + outcome_report
- `ExperimentManager.compare_experiment()` → `ComparisonResult`，自动计算：
  - 各组平均/最低口碑、最终热度、监管等级
  - 相对对照组的每人口碑差值
  - 最佳策略组推荐
- Web API：`POST /experiment/create`、`POST /experiment/{id}/run`、`GET /experiment/{id}/compare`、`GET /experiments`

## 开发路线图

- [x] Phase 1: 基础框架 - 多 Agent 仿真核心架构
- [x] Phase 2: 知识图谱 - 基于 GraphRAG 的关系管理与图推理上下文注入
- [x] Phase 3: 危机仿真引擎 - 时序 GraphRAG + 多 Agent 公关危机模拟 + what-if 干预 + 结果对比
- [x] Phase 4: 深度人格建模 - 10 维确定性人格，10+ 类图谱数据源
- [x] Phase 5: 自由组局 + 丰富干预 + 多样交互 + 对照实验
- [x] Phase 6: 系统增强 - 结构化记忆 + gossip_type决策 + 关系强度加权 + 观众语义分析 + LLM增强 + 引擎修复 + 102测试
- [ ] Phase 7: 扩展规模 - 支持 50+ Agent 并行交互

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Observer Agent                          │
│                 (群体分析 & 报告生成)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ 监控所有交互
┌──────────────────────────▼──────────────────────────────────┐
│                  CrisisSimulation (仿真引擎)                  │
│        时间线 | 6阶段生命周期 | 干预系统 | 观众反应          │
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
│ +危机角色  │   │+危机角色 │      │ +危机角色    │
└───────────┘   └─────────┘      └─────────────┘
      │               │                   │
      └───────────────┴───────────────────┘
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
  3. 随机顺序决策：Agent 每日随机排序依次行动           │
     └→ 后决策者看到前面人的动作 + 观众反应             │
     └→ 关系影响（strength加权）：配偶道歉→缓和，对手反击→强硬│
     └→ 传播效应：亲密关系者重大动作触发额外响应         │
     └→ gossip_type驱动：涉毒禁反击，离婚倾向声明       │
     └→ 记忆驱动：连续沉默→紧迫感，多次道歉无效→切换策略 │
  4. MessageBus → 观众反应+明星动作写入消息总线         │
  5. AudiencePool → 30个观众Agent生成评论（带记忆去重） │
  6. CrisisActionSpace / FreeActionSpace → 计算效果    │
  7. 谣言辟谣：STATEMENT/LAWSUIT 可辟谣（40%/60%）    │
  8. InformationVacuumDetector → 沉默触发谣言          │
  9. 热搜/媒体/品牌/监管 状态更新                       │
 10. 自然衰减（热度-10%/天，口碑按角色差异化回归）      │
 11. 动态终止：热度<15连续3天 或 监管满级 → 提前结束    │
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

- **随机顺序决策**：每天随机打乱 Agent 决策顺序，避免固定先手/后手偏差
- **关系影响（strength加权）**：基于知识图谱中的关系类型和强度，对方的动作按关系强度比例影响决策
  - 配偶道歉 → 自己也倾向缓和（权重 × strength）
  - 对手反击 → 自己也倾向强硬（权重 × strength）
  - 被指名 → 必须回应（声明加权 +2.0，不受 strength 影响）
- **八卦类型感知**：不同危机类型驱动不同策略
  - 出轨（CHEATING）：加害者倾向道歉隐退，受害者倾向声明起诉
  - 涉毒/偷税（DRUGS/TAX_EVASION）：强制隐退+公益，禁止反击/复出/卖惨
  - 离婚（DIVORCE）：倾向声明，各方相对中立
  - 丑闻（SCANDAL）：倾向声明+上节目澄清
- **观众反应（语义分析）**：30 个观众 Agent（粉丝 40%/路人 30%/理中客 20%/黑粉 10%）生成评论
  - 观众有记忆：重复动作降低评论概率，语义相似动作共享惩罚
  - 明星从评论提取关键词："道歉"→APOLOGIZE、"真相"→STATEMENT、"封杀"→HIDE、"起诉"→LAWSUIT
- **记忆驱动决策**：
  - 连续沉默 3 天+ → 紧迫感提升，倾向主动出击
  - 多次道歉无效（口碑仍低）→ 切换策略（隐退/公益）
  - 传播标记被读取：亲密关系者的重大动作触发额外回应
- **社交传播**：亲密关系者做了重大动作（道歉/反击/卖惨）→ 触发额外响应标记
- **MessageBus 集成**：观众反应和明星动作通过消息总线广播，实现真正的消息流转

### 角色感知决策

系统自动从知识图谱关系推断每个 Agent 在危机中的角色：

| 角色 | 说明 | 决策特征 |
|------|------|---------|
| PERPETRATOR（加害者） | 出轨方/涉毒者/逃税者 | 禁止复出/卖惨/反击，倾向道歉和隐退；口碑回归极慢（上限25，封杀线15以下不回归） |
| VICTIM（受害者） | 被出轨方/受害者 | 倾向发声明/起诉，不道歉；口碑恢复快（上限60，速率0.8） |
| ACCOMPLICE（第三者） | 绯闻对象/同谋 | 禁止复出/卖惨，倾向隐退和道歉；口碑回归慢（上限30） |
| BYSTANDER（旁观者） | 默认 | 无特殊修正，行为与修改前一致 |

**推断逻辑**：CHEATING 类型根据"配偶"和"绯闻对象"关系自动推断三角色；DRUGS/TAX_EVASION 类型根据 `involved_in` 边的 `role` 字段推断主当事人；DIVORCE 类型识别配偶/前配偶关系，双方默认 VICTIM；SCANDAL 类型查找 `involved_in` 中 `role=primary/subject` 的人标记为 PERPETRATOR。关系影响也针对绯闻对象和前配偶做了专门处理。

### 自由互动模式

除危机模式外，还支持自由互动模式（`InteractionMode.FREE`），使用 8 种 `FreeAction`：公开发言、支持声援、公开批评、合作联名、社交聚餐、宣布消息、无视冷处理、私信沟通。`FreeActionSpace` 提供简化效果计算（无阶段修正），`persona_agent.py` 中的 `_rule_decide_free()` 基于性格 + 关系 + 观众反应综合决策。

### A/B 对照实验

`ExperimentManager`（`swarmsim/crisis/experiment.py`）支持同一场景多组不同干预配置的并行对比：

- 创建实验：指定场景 + 多个实验组（每组独立干预列表）
- 运行实验：依次运行每组仿真，收集完整历史和结局报告
- 对比结果：自动计算各组平均口碑、最低口碑、热度、监管等级，找出最佳策略组
- 每人口碑差值：各实验组相对于对照组的口碑变化量
- Web API：`POST /api/crisis/experiment/create`、`POST /api/crisis/experiment/{id}/run`、`GET /api/crisis/experiment/{id}/compare`

## 许可证

MIT License
