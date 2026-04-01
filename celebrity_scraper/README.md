# 明星八卦爬虫系统

## 📋 概述

这是一个多源明星八卦数据爬取系统，支持从多个平台收集明星的社交媒体动态、新闻、评论和八卦信息。

## 🎯 主要功能

### 数据源支持

1. **百度百科** - 基础信息、个人简介、作品列表、人物关系、争议事件
2. **微博 (weibo.cn)** - 动态发布、粉丝数据、互动数据（基于 [weiboSpider](https://github.com/dataabc/weiboSpider) 封装）
3. **知乎** - 相关讨论、问答内容
4. **豆瓣** - 小组讨论、评论内容
5. **娱乐新闻** - 多平台新闻聚合（新浪、搜狐、网易、凤凰、腾讯）

### 双源爬取模式

系统采用**百度百科 + 微博**双源爬取策略：

- **百度百科**：提供明星基础资料（简介、出生日期、身高、职业、代表作品、经纪公司）、人物关系（配偶、前配偶、子女）、争议事件
- **微博**：提供实时社交数据（粉丝数、微博动态、点赞/转发/评论数、话题标签）

通过 `update_weibo_data.py` 一键完成双源爬取并合并数据。

### 数据类型

- **明星资料**: 姓名、生日、职业、经纪公司、代表作等
- **社交媒体**: 微博/抖音动态、互动数据
- **评论数据**: 热门评论、回复内容
- **新闻文章**: 娱乐新闻、情感分析
- **八卦事件**: 绯闻、争议、婚恋等八卦
- **人物关系**: 配偶、前任、同事等关系图谱

## 📁 项目结构

```
celebrity_scraper/
├── models.py              # 数据模型定义
├── scraper.py             # 主爬虫调度器（支持 mock/api/deep 三种模式）
├── mock_data.py           # 模拟数据生成器
├── weibo_uid_map.json     # 明星名 → 微博 UID 映射
├── spiders/
│   ├── __init__.py
│   ├── baidu_baike.py     # 百度百科（异步 httpx）
│   ├── weibo.py           # 微博（移动端 API）
│   ├── weibo_deep_spider.py  # 微博深度爬虫（weibo.cn HTML + cookie，基于 weiboSpider）
│   ├── zhihu.py           # 知乎
│   ├── douban.py          # 豆瓣
│   └── news.py            # 娱乐新闻
├── utils/
│   └── anti_spider.py     # 反爬虫工具
├── data/                  # 数据输出目录（JSON 格式）
└── COOKIE_GUIDE.md        # 微博 Cookie 获取指南
```

## 🚀 使用方法

### 1. 测试模式（模拟数据）

```bash
# 快速测试
python test_scraper.py

# 模拟指定明星
python test_scraper.py mock 杨幂

# 批量测试
python test_scraper.py batch

# 查看可用明星
python test_scraper.py list
```

### 2. 真实数据更新（百度百科 + 微博）

推荐使用独立的 `update_weibo_data.py` 脚本，双源爬取并完全替换数据：

```bash
# 设置 Cookie（三选一）
# 方式1: 命令行直接传入
python update_weibo_data.py --cookie "YOUR_COOKIE" --names 杨幂 赵丽颖

# 方式2: 从文件读取
python update_weibo_data.py --cookie-file weibo_cookie.txt --all

# 方式3: 写入 .env（推荐，一劳永逸）
echo 'WEIBO_COOKIE=YOUR_COOKIE' >> .env
python update_weibo_data.py --names 杨幂

# 验证 Cookie 是否有效
python update_weibo_data.py --validate

# 更新全部明星
python update_weibo_data.py --all

# 指定微博爬取页数（默认 3 页）
python update_weibo_data.py --names 杨幂 --pages 5
```

**Cookie 获取方法**：参见 `celebrity_scraper/COOKIE_GUIDE.md`

### 3. 使用爬虫模块代码

```python
from celebrity_scraper.scraper import CelebrityScraper

# Mock 模式
scraper = CelebrityScraper(mock_mode=True)
result = await scraper.scrape_celebrity("杨幂")

# Deep 模式（微博深度爬取）
scraper = CelebrityScraper(mock_mode=False, weibo_mode="deep", weibo_cookie="YOUR_COOKIE")
result = await scraper.scrape_celebrity("杨幂")
```

### 4. 批量爬取

```bash
python -m celebrity_scraper.scraper
```

## 📊 数据模型

### CelebrityProfile（明星资料）

```python
{
    "name": "杨幂",
    "english_name": "Yang Mi",
    "birth_date": "1986-09-12",
    "birth_place": "北京市",
    "occupation": ["演员", "歌手", "制片人"],
    "company": "嘉行传媒",
    "biography": "...",
    "famous_works": ["宫", "三生三世十里桃花", ...],
    "weibo_followers": 60000000
}
```

### GossipItem（八卦事件）

```python
{
    "title": "李小璐贾乃亮婚姻危机事件",
    "gossip_type": "cheating",
    "content": "2017年底，李小璐被拍到...",
    "date": "2017-12-29",
    "importance": 0.95,
    "verified": true,
    "involved_celebrities": ["李小璐", "贾乃亮", "PG One"]
}
```

### NewsArticle（新闻文章）

```python
{
    "title": "杨幂现身机场...",
    "content": "...",
    "source": "新浪娱乐",
    "sentiment": "positive",
    "sentiment_score": 0.5
}
```

## 🔧 配置说明

### 反爬虫配置

在 `utils/anti_spider.py` 中可以配置：

- **RateLimiter**: 请求频率限制
- **UserAgentRotator**: UA轮换
- **ProxyConfig**: 代理配置

### 环境变量

```bash
# 代理设置（可选）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# API密钥（如需要）
GEMINI_API_KEY=your_key

# 微博 Cookie（weibo.cn，用于深度爬取）
WEIBO_COOKIE=SCF=xxx; SUB=xxx; ...
```

### 微博 UID 映射

`weibo_uid_map.json` 维护明星名到微博 UID 的映射。当前已配置 10 位明星：

| 明星 | 微博 UID |
|------|---------|
| 肖战 | 1792951112 |
| 王一博 | 5492443184 |
| 杨幂 | 1195242865 |
| 赵丽颖 | 1259110474 |
| 迪丽热巴 | 1669879400 |
| 唐嫣 | 1230663070 |
| 罗晋 | 1219847813 |
| 李小璐 | 1191044977 |
| 贾乃亮 | 1214435497 |
| PG One | (空，账号已封禁) |

## 📝 输出格式

每个明星的数据保存为JSON文件：

```json
{
    "celebrity": {...},
    "gossips": [...],
    "relationships": [...],
    "social_media_posts": [...],
    "comments": [...],
    "news_articles": [...],
    "statistics": {
        "data_completeness": 0.95,
        "total_posts": 28,
        "total_comments": 70,
        ...
    }
}
```

## ⚠️ 注意事项

1. **微博 Cookie**: 深度爬取需要有效的 weibo.cn Cookie，过期后需重新获取
2. **请求频率**: 已内置随机延迟（3-6 秒），避免请求过快被封
3. **数据质量**: 百度百科页面结构可能变化导致解析失败；微博动态包含跨年时间戳自动处理
4. **反爬虫措施**: 多数平台有反爬虫机制，真实爬取可能失败
5. **Cookie 安全**: 不要将 Cookie 提交到版本控制，`.gitignore` 已排除 `weibo_cookie.txt`

## 🔄 后续改进方向

1. **Selenium/Playwright**: 支持JavaScript渲染页面
2. **代理池**: 自动轮换代理IP
3. **验证码处理**: 集成验证码识别
4. **增量更新**: 只爬取新数据
5. **GraphRAG集成**: 构建明星关系知识图谱

## 📄 许可证

MIT License
