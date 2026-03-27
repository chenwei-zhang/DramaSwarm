"""
娱乐新闻爬虫 - 爬取明星八卦新闻
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, quote
import httpx

from ..models import NewsArticle, Comment, GossipType, DataSourceType
from ..utils import RateLimiter, UserAgentRotator


# 娱乐新闻网站配置
NEWS_SOURCES = {
    "sina": {
        "name": "新浪娱乐",
        "base_url": "https://ent.sina.com.cn",
        "search_url": "https://search.sina.com.cn/",
        "list_selectors": [".blk-line-02 li", ".news-item", "article"],
        "title_selectors": ["h3 a", "a.title", ".title"],
        "summary_selectors": [".blk-line-02 p", ".summary", ".desc"],
        "time_selectors": [".time", ".date", ".pub-time"],
    },
    "sohu": {
        "name": "搜狐娱乐",
        "base_url": "https://yule.sohu.com",
        "search_url": "https://m.sohu.com/api/search",
        "list_selectors": [".news-list .item", "article"],
        "title_selectors": ["h3 a", "a.title"],
        "summary_selectors": [".summary", ".desc", "p"],
        "time_selectors": [".time", ".date"],
    },
    "ifeng": {
        "name": "凤凰网娱乐",
        "base_url": "https://ent.ifeng.com",
        "search_url": "https://so.ifeng.com/",
        "list_selectors": [".newsList li", ".item"],
        "title_selectors": ["h3 a", "a.title"],
        "summary_selectors": [".p", "p"],
        "time_selectors": [".time", ".date"],
    },
    "163": {
        "name": "网易娱乐",
        "base_url": "https://ent.163.com",
        "search_url": "https://so.163.com/",
        "list_selectors": [".news-item", "article"],
        "title_selectors": ["h3 a", "a.title"],
        "summary_selectors": [".summary", ".desc"],
        "time_selectors": [".time", ".date"],
    },
    "qq": {
        "name": "腾讯娱乐",
        "base_url": "https://ent.qq.com",
        "search_url": "https://www.qq.com/search/",
        "list_selectors": [".Q-tpList", ".item"],
        "title_selectors": ["h3 a", "a.title"],
        "summary_selectors": [".summary", ".desc"],
        "time_selectors": [[".time"], [".date"]],
    }
}


class EntertainmentNewsSpider:
    """娱乐新闻爬虫"""

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=1.0, max_delay=2.5, requests_per_minute=30)
        self.ua_rotator = UserAgentRotator()
        self.client = None

    async def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None or self.client.is_closed:
            headers = self.ua_rotator.get_headers()
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })

            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                verify=False
            )

        return self.client

    async def search_celebrity_news(self, celebrity_name: str, count: int = 30) -> list[NewsArticle]:
        """搜索明星相关新闻"""
        all_news = []

        # 从多个源搜索
        for source_key, source_info in NEWS_SOURCES.items():
            try:
                news = await self._search_from_source(celebrity_name, source_key, source_info, count // 4 + 5)
                all_news.extend(news)
                print(f"    {source_info['name']}: {len(news)} 条")

                await asyncio.sleep(1.5)

                if len(all_news) >= count:
                    break
            except Exception as e:
                print(f"    {source_info['name']}: 搜索失败 - {e}")

        return all_news[:count]

    async def _search_from_source(
        self,
        celebrity_name: str,
        source_key: str,
        source_info: dict,
        count: int
    ) -> list[NewsArticle]:
        """从特定来源搜索新闻"""
        news_list = []

        try:
            client = await self._get_client()

            # 构建搜索/列表URL
            search_url = self._build_search_url(celebrity_name, source_key, source_info)

            await self.rate_limiter.acquire()
            response = await client.get(search_url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 解析新闻列表
                news_items = self._parse_news_list(soup, source_info, celebrity_name)

                # 获取详细内容（限制数量）
                for item in news_items[:count]:
                    detail = await self._scrape_news_detail(item, client, source_info)
                    if detail:
                        news_list.append(detail)
                    await asyncio.sleep(0.5)

        except Exception as e:
            pass

        return news_list

    def _build_search_url(self, celebrity_name: str, source_key: str, source_info: dict) -> str:
        """构建搜索URL"""
        base_url = source_info["base_url"]

        # 简化的搜索策略 - 直接访问可能的新闻列表页
        url_patterns = {
            "sina": f"{base_url}/s/index.shtml",  # 新浪娱乐首页
            "sohu": f"{base_url}/",
            "ifeng": f"{base_url}/",
            "163": f"{base_url}/",
            "qq": f"{base_url}/",
        }

        return url_patterns.get(source_key, base_url)

    def _parse_news_list(self, soup: BeautifulSoup, source_info: dict, celebrity: str) -> list[dict]:
        """解析新闻列表"""
        news_items = []

        # 八卦相关的关键词
        gossip_keywords = ['八卦', '绯闻', '恋情', '分手', '结婚', '离婚', '争议', '丑闻',
                         '爆料', '曝光', '疑似', '传闻', '被拍', '深夜', '同住']

        # 使用配置的选择器
        for list_selector in source_info.get("list_selectors", []):
            items = soup.select(list_selector)

            if items:
                for item in items:
                    try:
                        # 提取标题和链接
                        title_elem = None
                        for title_sel in source_info.get("title_selectors", []):
                            title_elem = item.select_one(title_sel)
                            if title_elem:
                                break

                        if not title_elem:
                            title_elem = item.select_one("a")

                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get('href', '')

                            # 过滤：包含明星名或八卦关键词
                            if celebrity in title or any(kw in title for kw in gossip_keywords):
                                # 提取摘要
                                summary = ""
                                for summary_sel in source_info.get("summary_selectors", []):
                                    summary_elem = item.select_one(summary_sel)
                                    if summary_elem:
                                        summary = summary_elem.get_text(strip=True)
                                        break

                                # 提取时间
                                publish_date = ""
                                for time_sel in source_info.get("time_selectors", []):
                                    time_elem = item.select_one(time_sel)
                                    if time_elem:
                                        publish_date = time_elem.get_text(strip=True)
                                        break

                                if url:
                                    # 补全URL
                                    if not url.startswith('http'):
                                        url = urljoin(source_info["base_url"], url)

                                    news_items.append({
                                        "title": title,
                                        "url": url,
                                        "summary": summary,
                                        "publish_date": publish_date,
                                        "source": source_info["name"]
                                    })

                    except Exception:
                        continue

                if news_items:
                    break

        return news_items

    async def _scrape_news_detail(self, item: dict, client: httpx.AsyncClient, source_info: dict) -> Optional[NewsArticle]:
        """爬取新闻详情"""
        try:
            response = await client.get(item["url"])

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 提取正文内容
                content = self._extract_article_content(soup)

                if content and len(content) > 50:
                    # 提取作者
                    author = self._extract_author(soup)

                    # 提取发布时间
                    publish_date = self._extract_publish_time(soup)
                    if not publish_date:
                        publish_date = item.get("publish_date", "")

                    # 提取图片
                    images = self._extract_images(soup, item["url"])

                    # 提取标签
                    tags = self._extract_tags(soup)

                    # 情感分析
                    sentiment_score = self._analyze_sentiment(content + " " + item["title"])
                    sentiment = "positive" if sentiment_score > 0.1 else "negative" if sentiment_score < -0.1 else "neutral"

                    # 判断八卦类型
                    gossip_types = self._classify_gossip_type(item["title"] + " " + content)

                    return NewsArticle(
                        title=item["title"],
                        content=content,
                        summary=item.get("summary", "")[:200],
                        publish_date=publish_date,
                        author=author,
                        source=item["source"],
                        source_url=item["url"],
                        source_type=self._get_source_type(item["source"]),
                        images=images,
                        tags=tags,
                        sentiment=sentiment,
                        sentiment_score=sentiment_score,
                        related_gossip_types=gossip_types
                    )

        except Exception as e:
            pass

        return None

    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """提取文章正文"""
        content = ""

        # 常见的正文选择器
        content_selectors = [
            'article',
            '.article-content',
            '.article-body',
            '.news-content',
            '#article',
            '#artibody',
            '.content',
            '.main-content',
            '.post-content',
            '[itemprop="articleBody"]',
        ]

        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                # 移除广告等干扰内容
                for ad in elem.select('.ad, .advertisement, script, style, nav, footer'):
                    ad.decompose()

                paragraphs = elem.find_all('p')
                if paragraphs:
                    content = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                else:
                    content = elem.get_text(separator='\n', strip=True)

                if len(content) > 100:
                    content = content[:3000]  # 限制长度
                    break

        return content

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者"""
        author_selectors = [
            '.author',
            '.writer',
            '.byline',
            'article .meta .author',
            '[itemprop="author"]',
        ]

        for selector in author_selectors:
            elem = soup.select_one(selector)
            if elem:
                author = elem.get_text(strip=True)
                if author and len(author) < 50:
                    return author

        return ""

    def _extract_publish_time(self, soup: BeautifulSoup) -> str:
        """提取发布时间"""
        time_selectors = [
            '.publish-time',
            '.time',
            '.date',
            'article .meta .time',
            'time',
            '[itemprop="datePublished"]',
        ]

        for selector in time_selectors:
            elem = soup.select_one(selector)
            if elem:
                time_text = elem.get_text(strip=True)
                if time_text and re.search(r'\d', time_text):
                    return time_text

            # 也检查datetime属性
            elem = soup.select_one(selector)
            if elem:
                datetime_attr = elem.get('datetime') or elem.get('data-time')
                if datetime_attr:
                    return datetime_attr

        return ""

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """提取图片"""
        images = []

        for img in soup.select('article img, .content img, .article img')[:10]:
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                if not src.startswith('http'):
                    src = urljoin(base_url, src)
                images.append(src)

        return images

    def _extract_tags(self, soup: BeautifulSoup) -> list[str]:
        """提取标签"""
        tags = []

        tag_selectors = [
            '.tags a',
            '.keywords a',
            '.tag',
            'article .tags a',
        ]

        for selector in tag_selectors:
            elems = soup.select(selector)
            for elem in elems:
                tag = elem.get_text(strip=True)
                if tag and tag not in tags:
                    tags.append(tag)

        return tags[:10]

    def _analyze_sentiment(self, text: str) -> float:
        """简单的情感分析"""
        # 正面词汇
        positive_words = [
            '成功', '优秀', '精彩', '出色', '完美', '值得', '喜欢', '支持',
            '幸福', '快乐', '甜蜜', '浪漫', '感动', '敬佩', '赞美', '祝贺',
            '获得', '赢得', '登顶', '夺冠', '突破', '惊艳', '绝美', '爆红',
            '好评', '称赞', '掌声', '荣耀', '辉煌', '华丽', '精致'
        ]

        # 负面词汇
        negative_words = [
            '失败', '争议', '批评', '质疑', '丑闻', '分手', '离婚', '撕逼',
            '翻车', '塌房', '被封', '道歉', '被骂', '抵制', '指责', '出轨',
            '欺骗', '背叛', '黑料', '凉凉', '渣男', '绿茶', '炒作', '虚假',
            '令人失望', '批评声', '质疑声', '争议不断', '负面', '差评', '吐槽'
        ]

        # 中性/八卦词汇
        gossip_words = [
            '疑似', '传闻', '爆料', '曝光', '被拍', '深夜', '同住', '密会',
            '绯闻', '恋情', '八卦', '否认', '承认', '回应', '声明', '澄清'
        ]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        gossip_count = sum(1 for word in gossip_words if word in text)

        total = positive_count + negative_count + gossip_count
        if total == 0:
            return 0.0

        # 八卦词汇偏向中性略负
        score = (positive_count - negative_count - gossip_count * 0.2) / total

        return max(-1.0, min(1.0, score))

    def _classify_gossip_type(self, text: str) -> list[GossipType]:
        """判断八卦类型"""
        types = []

        type_keywords = {
            GossipType.ROMANCE: ['恋情', '恋爱', '约会', '牵手', '接吻', '亲密', '情侣'],
            GossipType.BREAKUP: ['分手', '分手了', '结束', '分手'],
            GossipType.MARRIAGE: ['结婚', '婚礼', '领证', '登记', '大婚'],
            GossipType.DIVORCE: ['离婚', '离婚证', '离婚诉讼'],
            GossipType.CHEATING: ['出轨', '劈腿', '偷情', '小三', '出轨门'],
            GossipType.SCANDAL: ['丑闻', '门', '事件', '风波'],
            GossipType.CONTROVERSY: ['争议', '质疑', '批评', '吐槽'],
            GossipType.RUMOR: ['传闻', '疑似', '被曝', '或', '据传'],
        }

        for gossip_type, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                types.append(gossip_type)

        if not types:
            types.append(GossipType.OTHER)

        return types

    def _get_source_type(self, source_name: str) -> DataSourceType:
        """根据来源名称获取数据源类型"""
        mapping = {
            "新浪娱乐": DataSourceType.SINA,
            "搜狐娱乐": DataSourceType.SOHU,
            "凤凰网娱乐": DataSourceType.IFENG,
            "网易娱乐": DataSourceType.NETEASE,
        }
        return mapping.get(source_name, DataSourceType.SINA)

    async def search_gossip_keywords(self, celebrity_name: str) -> list[NewsArticle]:
        """搜索八卦相关新闻"""
        gossip_keywords = [
            f"{celebrity_name} 绯闻",
            f"{celebrity_name} 八卦",
            f"{celebrity_name} 争议",
            f"{celebrity_name} 恋情",
            f"{celebrity_name} 分手",
        ]

        all_gossip = []

        for keyword in gossip_keywords:
            try:
                news = await self.search_celebrity_news(keyword, count=10)
                all_gossip.extend(news)

                await asyncio.sleep(2)

                if len(all_gossip) >= 50:
                    break
            except Exception as e:
                pass

        # 去重
        seen_urls = set()
        unique_gossip = []
        for news in all_gossip:
            if news.source_url and news.source_url not in seen_urls:
                seen_urls.add(news.source_url)
                unique_gossip.append(news)

        return unique_gossip[:50]

    async def get_hot_topics(self) -> list[dict]:
        """获取娱乐热点话题"""
        hot_topics = []

        # 从各网站获取热点
        for source_key, source_info in list(NEWS_SOURCES.items())[:2]:
            try:
                client = await self._get_client()
                url = source_info["base_url"]

                await self.rate_limiter.acquire()
                response = await client.get(url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 解析热点标题
                    hot_selectors = [
                        '.hot-list a',
                        '.hot-topic a',
                        'h3 a',
                        '.title a',
                    ]

                    for selector in hot_selectors:
                        items = soup.select(selector)[:10]
                        for item in items:
                            title = item.get_text(strip=True)
                            href = item.get('href', '')

                            if title and len(title) > 5 and len(title) < 50:
                                hot_topics.append({
                                    "title": title,
                                    "url": urljoin(source_info["base_url"], href),
                                    "source": source_info["name"]
                                })

                        if hot_topics:
                            break

            except Exception:
                pass

        return hot_topics[:30]

    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
