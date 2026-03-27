# 明星八卦爬虫系统

## 📋 概述

这是一个多源明星八卦数据爬取系统，支持从多个平台收集明星的社交媒体动态、新闻、评论和八卦信息。

## 🎯 主要功能

### 数据源支持

1. **百度百科** - 基础信息、个人简介、作品列表
2. **微博** - 动态发布、粉丝互动、热搜话题
3. **知乎** - 相关讨论、问答内容
4. **豆瓣** - 小组讨论、评论内容
5. **娱乐新闻** - 多平台新闻聚合（新浪、搜狐、网易、凤凰、腾讯）

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
├── models.py          # 数据模型定义
├── scraper.py         # 主爬虫调度器
├── mock_data.py       # 模拟数据生成器
├── spiders/
│   ├── __init__.py
│   ├── baidu_baike.py # 百度百科
│   ├── weibo.py       # 微博
│   ├── zhihu.py       # 知乎
│   ├── douban.py      # 豆瓣
│   └── news.py        # 娱乐新闻
├── utils/
│   └── anti_spider.py # 反爬虫工具
└── data/              # 数据输出目录
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

### 2. 真实爬取模式

```bash
# 爬取单个明星（可能因反爬措施失败）
python test_scraper.py real 杨幂

# 使用代码
from celebrity_scraper.scraper import CelebrityScraper

scraper = CelebrityScraper(
    output_dir="celebrity_scraper/data",
    enable_all_sources=True,
    mock_mode=False  # 设为False进行真实爬取
)
result = await scraper.scrape_celebrity("杨幂")
```

### 3. 批量爬取

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
```

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

1. **反爬虫措施**: 多数平台有反爬虫机制，真实爬取可能失败
2. **模拟模式**: 建议先使用模拟模式测试功能
3. **请求频率**: 已内置限流器，避免请求过快
4. **数据质量**: 网页结构变化可能导致解析失败

## 🔄 后续改进方向

1. **Selenium/Playwright**: 支持JavaScript渲染页面
2. **代理池**: 自动轮换代理IP
3. **验证码处理**: 集成验证码识别
4. **增量更新**: 只爬取新数据
5. **GraphRAG集成**: 构建明星关系知识图谱

## 📄 许可证

MIT License
