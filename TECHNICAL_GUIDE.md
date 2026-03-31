# DramaSwarm 技术白皮书

> 娱乐圈危机公关仿真引擎：从知识图谱到危机推演

---

## 一、系统概述

DramaSwarm 是一个面向中国娱乐圈的多智能体危机公关仿真系统。它用 **知识图谱** 存储明星关系、八卦事件、新闻报道等结构化数据，在此基础上运行**危机仿真引擎** — 从历史八卦事件中加载场景，多个明星 Agent 顺序决策、观众 Agent 生成评论、关系类型影响行为选择。

引擎集成了 LLM 集成层和独立的危机环境模型。

---

## 二、核心数据结构：知识图谱

### 2.1 图引擎选型

知识图谱基于 **networkx `MultiDiGraph`**（有向多重图）实现。选择多重图而非简单图的原因：同一对明星之间可能存在多种关系（如"搭档"+"好友"），需要多条并行边。

```
节点类型:
  celebrity:{name}   — 明星节点
  gossip:{title}     — 八卦事件节点
  news:{person}:{title[:30]}  — 新闻节点

边类型:
  relationship    — 明星↔明星（双向，带 relation_type/strength/confidence）
  involved_in     — 明星→事件（单向，带 role）
  simulation_event — 明星→明星（仿真中动态生成，带 severity/weight，可衰减）
```

### 2.2 时序索引

`TemporalKnowledgeGraph` 在基础图之上增加了两个索引结构：

- **`_timeline_index: list[tuple[str, str]]`** — 按日期排序的 `(date, node_id)` 元组列表。使用 `bisect.insort` 维护有序性，实现 O(log n + k) 的日期范围查询
- **`_person_timelines: dict[str, list[dict]]`** — 每个人物的时间线，包含所有相关事件（gossip + news）

这两个索引在加载数据时同步构建，查询时不需要遍历全图。

### 2.3 关键查询方法

| 方法 | 用途 | 算法 |
|------|------|------|
| `get_relationship_context(a, b)` | 获取两人间所有关系边 | 直接边迭代 |
| `get_social_neighborhood(name, depth)` | BFS 获取社交邻居 | 广度优先搜索，支持深度控制 |
| `find_connection_path(a, b)` | 两人间最短路径 | 构建无向图 → `nx.shortest_path` |
| `get_event_impact(text, agent)` | 事件对 Agent 的影响程度 | 关系类型 → 影响权重映射（配偶 0.3 > 前任 0.25 > 绯闻 0.2 > 搭档 0.15） |
| `get_events_in_range(start, end)` | 日期范围内的事件 | bisect 二分查找 |
| `find_mentioned_names(text)` | 文本中提及的明星 | 子串匹配所有已知人名 |

### 2.4 动态变更

仿真运行中，图谱支持三种运行时变更：

- `add_simulation_event()` — 添加仿真事件边（记录 Agent 间的互动）
- `update_relationship_strength()` — 调整关系强度（clamped 0-1）
- `decay_simulation_edges(rate=0.3)` — 衰减仿真边权重，低于 0.05 则删除。防止历史仿真数据无限积累

---

## 三、Agent 架构

### 3.1 双模式设计

`CelebrityPersonaAgent` 支持两种决策模式：

```
CelebrityPersonaAgent
├── 规则模式 — 从决策矩阵中基于性格/角色/阶段选择动作，零延迟
└── LLM 模式 — 调用 LLM 生成回复，失败时 fallback 到规则模式
```

两种模式共享 `perceive() → think() → speak()/act()` 的统一接口。

### 3.2 记忆系统

Agent 内部维护一个 `AgentMemory`，核心算法：

```
记忆条目: {timestamp, content, source, importance(0-1), tags}

衰减: 每轮 importance *= 0.95（5% 衰减率）
清理: 当条目数 > retention_turns * 10 时，
      保留 importance > 0.7 的 + 最近 retention_turns 条
检索: get_recent(n) / get_important(threshold, n) / search(query)
```

记忆的重要性由事件类型和性格共同决定：
- 高神经质 Agent 遇到冲突/批评 → importance = 0.8
- 高外向性 Agent 收到赞美/认可 → importance = 0.6
- 默认 → importance = 0.5

### 3.3 Big Five 性格模型

`CelebrityPersonaAgent` 使用大五人格模型（扩展为 10 维）：

```python
openness: float           # 开放性 — 影响接受新观点的意愿
conscientiousness: float  # 尽责性 — 影响遵循规则的程度
extraversion: float       # 外向性 — 影响主动发言、上节目的倾向
agreeableness: float      # 宜人性 — 影响道歉、妥协的倾向
neuroticism: float        # 神经质 — 影响反击、情绪化反应的倾向
```

性格特质影响两个层面：记忆编码（决定哪些事件被高权重记住）和行为输出（通过 LLM prompt 引导或规则权重调整）。

---

## 四、危机仿真引擎

### 4.1 整体架构

```
CrisisScenarioEngine          CrisisSimulation
  └─ 从图谱加载场景             └─ 异步运行仿真循环
  └─ _infer_person_roles()          │
       │  自动推断 PERPETRATOR/  CrisisTimeline (1天=1回合)
       │  VICTIM/ACCOMPLICE     6阶段生命周期
       │                              │
  TemporalKnowledgeGraph             step() 每日循环
  list_crisis_scenarios()               │
  get_crisis_scenario_data()            │
       ┌────────────────────────────┼─────────────────────────────┐
       │                            │                             │
  CelebrityPersonaAgent       AudiencePool               InterventionSystem
  (明星 Agent)                (观众 Agent 池)             (用户干预)
  Big Five + CrisisRole       粉丝/路人/理中客/黑粉        强制动作/外部事件
  规则/LLM 双模式             模板评论生成                    │
  角色感知决策                  │                             │
       │                            │                             │
       └──────────── MessageBus ──────────────────────────────────┘
                           (Agent 间消息总线)
```

### 4.2 顺序决策流程

`CrisisSimulation.step()` 的核心是 Agent 的顺序执行：

```python
# 伪代码
for name, agent in agents.items():
    peer_actions = 今天前面 Agent 已经做的动作
    audience_reactions = audience_pool.generate_reactions(peer_actions)

    action = agent.generate_crisis_response(
        phase, state,
        peer_actions=peer_actions,
        audience_reactions=audience_reactions,
    )
    day_actions.append(action)

    if action.triggered_by:
        interaction_log.append(触发关系记录)
```

这意味着：**第一个发言的 Agent 是"盲选"，最后一个 Agent 能看到所有人的动作和观众反应**。

### 4.3 关系影响矩阵

Agent 感知其他 Agent 的动作后，通过 `get_relationship_context()` 查询关系类型，调整决策权重：

| 关系类型 | 对方动作 | 我的影响 | 权重偏移 |
|---------|---------|---------|---------|
| 配偶/家人 | 道歉 | 倾向缓和 | 道歉+1.5, 声明+1.0 |
| 配偶/家人 | 反击 | 倾向强硬 | 反击+1.2, 声明+1.5 |
| 对手/宿敌 | 反击 | 也倾向反击 | 反击+1.5, 声明+1.0 |
| 对手/宿敌 | 道歉 | 高姿态沉默 | 沉默+1.5, 卖惨+1.0 |
| 对手/宿敌 | 卖惨 | 发声明澄清 | 声明+2.0 |
| 绯闻对象 | 道歉 | 倾向隐退 | 隐退+1.5, 声明+1.0 |
| 绯闻对象 | 反击 | 倾向声明 | 声明+1.5, 沉默+1.0 |
| 前配偶/前任 | 道歉 | 发声明表明立场 | 声明+1.5 |
| 前配偶/前任 | 反击 | 倾向起诉 | 起诉+2.0, 声明+1.5 |
| 任意 | 动作 target==自己 | 必须回应 | 声明+2.0, 反击+1.0 |

### 4.4 观众 Agent 池

`AudiencePool` 管理 30 个观众 Agent，按比例分配：

```
粉丝 (40%)  → 偏好 bias ∈ [0.3, 0.8]，其中一人 bias ∈ [0.7, 1.0]
路人 (30%)  → 偏好 bias ∈ [-0.3, 0.3]
理中客 (20%) → 偏好 bias ∈ [-0.1, 0.1]
黑粉 (10%)  → 偏好 bias ∈ [-0.8, -0.3]
```

评论生成概率 = `0.3 + |bias| × 0.5`。每个观众 Agent 对每条明星动作独立生成评论，内容从角色模板池中选取。

观众评论汇总后影响明星决策：
- 负面评论占比 > 60% → 道歉/沉默加权
- 负面评论占比 < 30% → 声明/反击加权

### 4.5 传播效应

`_check_propagation()` 检查一条动作是否会触发其他 Agent 的响应：

```
条件: 关系 ∈ (配偶, 前配偶, 伴侣, 家人, 亲属, 绯闻对象, 绯闻, 传闻)
      AND 动作 ∈ (道歉, 反击, 卖惨, 声明)
效果: 在目标 Agent 的 memory 中追加 PROPAGATION 标记

条件: 关系 ∈ (对手, 竞争对手, 宿敌, 同代竞争) AND 动作 ∈ (反击, 卖惨)
效果: 同上
```

传播标记不直接改变当轮决策，但通过记忆系统影响后续回合的行为倾向。

### 4.6 信息真空检测

`InformationVacuumDetector` 追踪每个人的沉默天数：

```
沉默天数  →  谣言生成概率
2天       →  30%
3天       →  50%
4天+      →  min(90%, 50% + (days-3) × 10%)
```

谣言影响：`approval -= severity × 8`，`heat += severity × 15`。这构成了一个正反馈循环——沉默导致谣言，谣言推高热度，高热度增加压力。

### 4.7 十种 PR 策略效果矩阵

| 动作 | 口碑Δ | 热度Δ | 谣言倍率 | 品牌Δ |
|------|-------|-------|---------|-------|
| 沉默 | 0 | +5 | 1.3 | -0.5 |
| 道歉 | +8 | -15 | 0.4 | +3 |
| 声明 | +3 | -5 | 0.7 | +1 |
| 上节目 | +5 | -10 | 0.3 | +2 |
| 起诉 | +2 | +5 | 0.5 | 0 |
| 卖惨 | +6 | -3 | 0.8 | -1 |
| 反击 | -5 | +20 | 0.4 | -3 |
| 隐退 | -3 | +3 | 1.5 | -2 |
| 公益 | +4 | -8 | 0.6 | +2 |
| 复出 | +2 | +10 | 1.0 | +1 |

**阶段修正器**（6 阶段 × 10 动作的 60 值矩阵）按场景阶段调整效果：

- 爆发期道歉效果 ×0.3（太快道歉显得心虚）
- 高峰期道歉效果 ×1.2（最佳道歉窗口）
- 余波期复出效果 ×1.3（最安全的复出时机）
- 余波期道歉效果 ×0.3（太晚了没有意义）

**性格修正器**（Big Five 特质 × 动作）：
- 高神经质 → 反击效果放大 `(1 + neuroticism × 0.3)`
- 高宜人性 → 道歉效果放大 `(1 + agreeableness × 0.2)`
- 低口碑惩罚：`approval < 30` 时，道歉/声明效果 ×0.7

### 4.8 危机生命周期

```
Day 0-1   爆发期 (BREAKOUT)    事件刚曝光，最佳策略是声明
Day 2-3   发酵期 (ESCALATION)  细节流出，沉默变得危险
Day 4-7   高峰期 (PEAK)        全网讨论，道歉/上节目最佳窗口
Day 8-14  应对期 (MITIGATION)  公关策略见效/失效，公益可做
Day 15-21 收尾期 (RESOLUTION)  降温，公益/复出可行
Day 22+   余波期 (AFTERMATH)   长期影响，复出最安全
```

### 4.9 每日衰减（角色差异化）

仿真中的自然衰减模拟了"时间是最好的公关"这一现实规律，但不同角色的恢复速度截然不同：

```
热度: heat *= 0.9              # 每天自然降 10%

口碑回归（角色差异化）:
  PERPETRATOR → 目标 25, 速率 0.1  # 出轨者回归极慢，上限低
  ACCOMPLICE  → 目标 30, 速率 0.15 # 第三者回归慢
  VICTIM      → 目标 60, 速率 0.8  # 受害者恢复快
  BYSTANDER   → 目标 50, 速率 0.5  # 默认

封杀线: PERPETRATOR 口碑 < 15 时不再回归（彻底封杀）

品牌: value → 50 方向回归       # 低于 50 每天回升 0.3，高于 50 每天下降 0.2
```

### 4.10 角色推断

`_infer_person_roles()` 从知识图谱关系自动推断各人角色：

**CHEATING 类型**：
1. 遍历 involved_persons 找"配偶/伴侣"关系对
2. 在剩余人中找与某配偶有"绯闻对象"关系的人 → 标记为 ACCOMPLICE
3. 配偶中有绯闻关系的一方 → PERPETRATOR，另一方 → VICTIM

**DRUGS/TAX_EVASION 类型**：
- 查找 `involved_in` 边的 `role` 字段为 "primary"/"主角"/"当事人" → PERPETRATOR

**其他类型**：全部 BYSTANDER（行为与修改前一致）

推断结果注入 `CelebrityPersonaAgent.crisis_role` 和 `gossip_type`，影响规则决策、LLM prompt、口碑衰减三个层面。

### 4.11 结果分析

`OutcomeAnalyzer` 对比仿真结果与历史基线：

1. 计算仿真指标（每人 min/final approval、max heat、谣言数、监管峰值等）
2. 对比 `scenario.historical_outcome` 中的真实结果
3. 判定 verdict：全员更好 / 全员更差 / 好坏参半
4. 生成 PR 建议（基于规则，如 `min_approval < 20 → "建议在危机早期及时道歉"`）

---

## 五、LLM 集成层

### 5.1 统一接口

```python
class LLMClient(ABC):
    generate(prompt, system_prompt, history) -> LLMResponse
    generate_async(prompt, system_prompt, history) -> LLMResponse
    chat(messages: list[Message]) -> LLMResponse       # 自动提取 system prompt
    chat_async(messages: list[Message]) -> LLMResponse
```

### 5.2 三家提供商

| 提供商 | SDK | 异步支持 | 错误处理 |
|--------|-----|---------|---------|
| Gemini | `google-genai` | 原生 async | 捕获所有异常，返回 `[LLM 错误]` 前缀 |
| OpenAI | `openai` | 同步透传 | 同上 |
| Anthropic | `anthropic` | 同步透传 | 同上 |

**注意**：在 FastAPI 的 asyncio 事件循环中，只能调用 `generate_async()`。`GeminiClient.generate()` 内部使用 `asyncio.run()`，在已有事件循环中会抛出 `RuntimeError`。

### 5.3 工厂函数

```python
get_client(provider=None, model=None)
# provider 从参数或 LLM_PROVIDER 环境变量读取（默认 gemini）
# model 从参数或 LLM_MODEL 环境变量读取
```

---

## 六、前端可视化

### 6.1 技术栈

- **后端**: FastAPI + uvicorn，两个 API 路由（graph/crisis）
- **前端**: 单文件 `index.html`，D3.js v7 力导向图 + Canvas 2D 折线图
- **无构建工具**: 纯 HTML/CSS/JS，通过 CDN 加载 D3

### 6.2 图谱序列化

`serializer.py` 将 networkx 图转为 D3 格式：

```
节点半径计算:
  celebrity: 18 + log10(max(weibo_followers, 1e4)) × 3   (~30-51)
  gossip:    10 + importance × 10                           (10-20)
  news:      固定 8

边去重:
  relationship 边在图中双向存储，序列化时只保留 (min, max) 方向
  同一对节点间多条不同类型的关系边通过 curve_offset 实现弧线分离
```

### 6.3 图谱交互

- 力导向布局：节点间斥力 -350，关系边长度按 strength 调节（120 - strength×40）
- 多边弧线：同一对节点间多条边按偏移量绘制贝塞尔曲线
- 节点类型区分：celebrity 为圆形、gossip 为旋转 45° 的菱形
- 路径高亮：`find_connection_path` 结果高亮显示，非路径节点降至 12% 不透明度

### 6.4 危机仿真面板

三栏布局：
- **左栏**: 场景选择、人物卡片（口碑条+品牌值+交互标记）、干预面板
- **中栏**: Canvas 口碑走势图（每人一条线+热度虚线）、事件时间线（含因果关系标记 `← 被XX触发`）
- **右栏**: 观众反应（情绪统计+评论）、热搜榜、媒体头条、品牌状态、结果对比

---

## 七、数据管线

### 7.1 数据采集

`celebrity_scraper/` 模块包含五个爬虫：

| 爬虫 | 目标站点 | 数据类型 |
|------|---------|---------|
| `baidu_baike.py` | 百度百科 | 基础资料、代表作、获奖 |
| `weibo.py` | 微博 | 粉丝数、社交动态 |
| `zhihu.py` | 知乎 | 讨论热度、事件分析 |
| `douban.py` | 豆瓣 | 作品评分、粉丝画像 |
| `news.py` | 新闻聚合 | 娱乐新闻报道 |

采集结果以 JSON 文件存储在 `celebrity_scraper/data/` 目录。

### 7.2 数据加载管线

```
JSON 文件目录
    │
    ▼
KnowledgeGraph.load_from_json_dir()
    │
    ├── Pass 1: 逐文件加载
    │   ├── _add_celebrity_node() → 节点已存在则合并属性（不覆盖）
    │   ├── _add_relationship_edge() → 双向添加，同类型去重
    │   ├── _add_gossip_node() → 创建事件节点 + involved_in 边
    │   └── _add_news_event() → 轻量新闻节点
    │
    ├── Pass 2: _deduplicate_gossip_nodes()
    │   └── 相同标题的 gossip 节点合并（边迁移到规范节点，删除副本）
    │
    └── TemporalKnowledgeGraph 扩展:
        ├── _timeline_index 更新（bisect.insort）
        └── _person_timelines 更新
```

---

## 八、设计模式与架构决策

### 8.1 使用的设计模式

| 模式 | 应用位置 | 说明 |
|------|---------|------|
| 策略 | 规则模式 vs LLM 模式 | 统一接口，不同决策策略 |
| 模板方法 | `step()` 骨架 | 按阶段分支决策路径 |
| 备忘录 | CrisisState 快照 | 完整状态快照 |
| 消息总线 | MessageBus | Agent 间解耦通信 |
| 工厂 | CrisisScenarioEngine | 场景加载与 Agent 创建 |

### 8.2 关键架构决策

1. **有向多重图 vs 简单图**：同一对明星可有多条不同类型的关系边（如"搭档"+"好友"），支持复杂关系网络的表达

2. **阶段基于天数而非事件驱动**：危机生命周期严格按天数映射阶段，简化实现且符合"时间压力"的现实感受

3. **观众池基于模板而非 LLM**：30 个观众 Agent 使用模板生成评论，避免大量 LLM 调用的延迟和成本

4. **顺序决策而非并行**：后决策的 Agent 能感知前面人的动作，创造更有意义的交互，但牺牲了并行性能

5. **规则优先 + LLM 可选**：所有决策逻辑都有纯规则 fallback，确保无 API key 时也能完整运行

6. **误差容忍的 LLM 集成**：三个提供商都 catch 全部异常返回错误消息，不向上抛出，保证仿真不因 LLM 故障中断

### 8.3 性能特征

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 日期范围查询 | O(log n + k) | bisect 二分 + k 个结果 |
| 人物时间线查询 | O(1) | 直接 dict 查找 |
| BFS 社交邻居 | O(V + E) | 标准 BFS |
| 最短路径 | O(V + E) | 转无向图后 Dijkstra |
| 单步仿真 | O(A × P) | A=Agent数, P=观众数 |

---

## 九、测试体系

### 9.1 测试结构

```
tests/
├── test_crisis_engine.py     # 28 个测试 — 时间线、动作空间、真空检测、干预系统
└── test_temporal_graph.py    # 9 个测试 — 时序索引、日期查询、场景提取
```

### 9.2 测试覆盖要点

- **Timeline**: 所有 6 个阶段的边界值测试
- **ActionSpace**: 10 动作 × 6 阶段 × Big Five 修正的完整效果验证
- **VacuumDetector**: 沉默 2/3/4+ 天的谣言触发概率
- **InterventionSystem**: 触发条件匹配、错误日期不触发、reset 清理
- **TemporalGraph**: 日期范围查询、人物事件过滤、场景提取完整性

---

## 十、五大增强特性

### 10.1 深度人格建模

`CelebrityPersonaAgent._build_personality()` 使用确定性哈希（`hashlib.md5(name + counter)`）替代 `random.uniform()`，保证同一明星每次仿真人格一致。

**10 维人格画像**，从 8 类图谱数据源推导：

| 维度 | 数据源 | 推导逻辑 |
|------|--------|----------|
| openness | 职业、关系网连接数 | 歌手/偶像 → 0.6-0.85，连接数≥10 → +0.15 |
| conscientiousness | 职业、作品数量 | 导演/制片 → 0.6-0.85，作品≥8 → +0.1 |
| extraversion | 职业、Bio关键词、粉丝量 | 主持人/歌手 → 高，"低调"关键词 → 低 |
| agreeableness | Bio关键词、关系类型 | "慈善" → 0.65-0.85，"火爆" → 0.25-0.45 |
| neuroticism | Bio关键词、历史事件 | 争议/出轨 → 0.55-0.8，吸毒/偷税 → 强制高 |
| risk_tolerance | 上述 5 维联合推导 | 0.3×neuroticism + 0.3×extraversion + 0.2×openness + 0.2×(1-agreeableness) |
| public_visibility | weibo_followers | ≥1亿 → 0.95，≥5000万 → 0.75，逐级递减 |
| career_stage | famous_works 数量 | ≥8 → 0.9，≥4 → 0.6，≥1 → 0.35 |
| media_savvy | company 关键词 | "工作室" → 0.7-0.9，"娱乐/影视" → 0.5-0.75 |
| controversy_history | 历史事件 importance 加总 | 总importance>2.0 或 ≥4事件 → 0.7-0.95 |

新增维度直接影响 `action_space.py` 中的效果修正：高 `risk_tolerance` → 反击/卖惨加强，高 `public_visibility` → 沉默代价增大，高 `media_savvy` → 声明/上节目效果放大。

### 10.2 自由组局

`CrisisScenarioEngine` 新增三个方法：

- `get_celebrities()` — 返回图谱中所有名人（名字+职业+粉丝数+代表作），按粉丝数降序
- `discover_relationships(persons)` — 遍历所有配对，调用 `kg.get_relationship_context()` 自动发现关系
- `create_custom_scenario(params)` — 验证人名存在、解析枚举、注册到可用场景

前端提供名人选择网格（最多 6 人，复选框），"发现关系"按钮展示已有关系图，"创建并启动"一键完成场景创建和仿真启动。

### 10.3 丰富干预维度

**三种触发类型**（`TriggerType` 枚举）：
- `TIME_ABSOLUTE` — 精确匹配指定日期
- `TIME_RELATIVE` — 从仿真开始后第 N 天
- `STATE_THRESHOLD` — 当 approval/heat/brand/regulatory 达到阈值时触发

**六种外部事件**（`ExternalEventType` 枚举）：
- `MEDIA_REPORT` / `VIDEO_LEAK` / `COMPETITOR_ANNOUNCE` / `REGULATORY_ACTION` / `BRAND_DECISION` / `CUSTOM`
- 每种事件有独立的 approval/heat/brand 效果模板，同时生成配套热搜和媒体头条

**关系变更**：`strengthen`(强度+0.2) / `weaken`(强度-0.2) / `break`(强度→0.05) / `new`(新建边)

### 10.4 自由互动模式

`FreeAction` 枚举定义 8 种自由互动动作：公开发言、支持声援、公开批评、合作联名、社交聚餐、宣布消息、无视冷处理、私信沟通。

`FreeActionSpace` 提供简化效果计算（无阶段修正），`persona_agent.py` 中的 `_rule_decide_free()` 基于性格 + 关系 + 观众反应综合决策：
- 高外向性 → 发言/社交加权
- 高宜人性 → 支持/调停加权
- 高神经质 → 批评/传谣加权
- 亲密关系者 → 支持加权，对手 → 批评加权

`CrisisSimulation.step()` 根据 `InteractionMode` 枚举自动分支危机/自由决策路径。

### 10.5 A/B 对照实验

`ExperimentManager`（`swarmsim/crisis/experiment.py`）支持同一场景多组不同干预配置的并行对比：

- `create_experiment()` — 创建实验（场景 + 多个实验组，每组独立干预列表）
- `run_experiment()` — 依次运行每组仿真，收集完整历史和结局报告
- `compare_experiment()` → `ComparisonResult`，自动计算：
  - 各组平均/最低口碑、热度、监管等级
  - 每人口碑差值（相对于对照组）
  - 最佳策略组推荐

API 端点：`POST /api/crisis/experiment/create`、`POST /api/crisis/experiment/{id}/run`、`GET /api/crisis/experiment/{id}/compare`、`GET /api/crisis/experiments`

---

*本文档最后更新：2026-03-30*
