"""
豆瓣爬虫 - 爬取明星相关讨论和影评
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional
from bs4 import BeautifulSoup
import httpx

from ..models import Comment, SocialMediaPost, DataSourceType
from ..utils import RateLimiter, UserAgentRotator


class DoubanSpider:
    """豆瓣爬虫"""

    BASE_URL = "https://www.douban.com"
    GROUP_URL = "https://www.douban.com/group"

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=2.0, max_delay=5.0, requests_per_minute=12)
        self.ua_rotator = UserAgentRotator()
        self.client = None

    async def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None or self.client.is_closed:
            headers = self.ua_rotator.get_headers()
            headers.update({
                "Referer": "https://www.douban.com",
            })

            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                verify=False,
                cookies=dict(dbcl2="")  # 豆瓣可能需要登录
            )

        return self.client

    async def search_celebrity(self, name: str) -> Optional[dict]:
        """搜索明星豆瓣页面"""
        await self.rate_limiter.acquire()

        try:
            client = await self._get_client()
            search_url = f"{self.BASE_URL}/search"
            params = {
                "q": name,
                "cat": "celebrity"
            }

            response = await client.get(search_url, params=params)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 查找明星条目
                items = soup.select('.item .title a')
                if items:
                    first_url = items[0].get('href', '')
                    if 'celebrity' in first_url:
                        return {"url": first_url, "name": name}

            return None

        except Exception as e:
            print(f"豆瓣搜索失败 {name}: {e}")
            return None

    async def search_group_topics(self, keyword: str, count: int = 20) -> list[SocialMediaPost]:
        """搜索豆瓣小组话题"""
        await self.rate_limiter.acquire()

        topics = []

        try:
            client = await self._get_client()
            search_url = f"{self.BASE_URL}/search"
            params = {
                "q": keyword,
                "cat": "group"
            }

            response = await client.get(search_url, params=params)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 解析话题列表
                topic_items = soup.select('.result .title a')[:count]

                for item in topic_items:
                    url = item.get('href', '')
                    title = item.get_text(strip=True)

                    # 获取话题详情
                    if url:
                        topic_detail = await self._scrape_group_topic(url)
                        if topic_detail:
                            topics.append(topic_detail)

                        if len(topics) >= count:
                            break

                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"豆瓣小组搜索失败 {keyword}: {e}")

        return topics

    async def _scrape_group_topic(self, url: str) -> Optional[SocialMediaPost]:
        """爬取豆瓣小组话题详情"""
        await self.rate_limiter.acquire()

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 提取作者
                author_elem = soup.select_one('.topic-doc .from a')
                author = author_elem.get_text(strip=True) if author_elem else ""

                # 提取内容
                content_elem = soup.select_one('.topic-content')
                content = content_elem.get_text(strip=True) if content_elem else ""

                # 提取回复数
                reply_count = len(soup.select('.reply-doc'))

                # 提取时间
                time_elem = soup.select_one('.topic-doc .create-time')
                publish_time = time_elem.get_text(strip=True) if time_elem else ""

                # 提取图片
                images = [img.get('src', '') for img in soup.select('.topic-content img')]

                # 提取标签
                tags = []
                tag_elems = soup.select('.topic-tags a')
                for tag in tag_elems:
                    tags.append(tag.get_text(strip=True))

                return SocialMediaPost(
                    id=url.split('/')[-1] if url else "",
                    platform="douban",
                    author=author,
                    author_id="",
                    content=content[:2000],
                    images=images[:5],
                    likes=0,
                    reposts=0,
                    comments=reply_count,
                    publish_time=publish_time,
                    source_url=url,
                    tags=tags
                )

        except Exception as e:
            print(f"爬取话题失败 {url}: {e}")

        return None

    async def scrape_topic_comments(self, url: str, count: int = 30) -> list[Comment]:
        """爬取话题评论"""
        await self.rate_limiter.acquire()

        comments = []

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 解析评论
                reply_docs = soup.select('.reply-doc')[:count]

                for reply in reply_docs:
                    author_elem = reply.select_one('.reply-info a')
                    author = author_elem.get_text(strip=True) if author_elem else ""

                    content_elem = reply.select_one('.reply-content')
                    content = content_elem.get_text(strip=True) if content_elem else ""

                    # 提取点赞数
                    likes_elem = reply.select_one('.lnks a')
                    likes_text = likes_elem.get_text() if likes_elem else ""
                    likes_match = re.search(r'(\d+)', likes_text)
                    likes = int(likes_match.group(1)) if likes_match else 0

                    comment = Comment(
                        id="",
                        content=content,
                        author=author,
                        likes=likes,
                        replies=0,
                        publish_time="",
                        source_platform="douban",
                        source_url=url
                    )
                    comments.append(comment)

        except Exception as e:
            print(f"爬取评论失败 {url}: {e}")

        return comments

    async def search_movie_celebrity_discussions(self, celebrity_name: str) -> list[dict]:
        """搜索明星电影相关的讨论"""
        discussions = []

        # 搜索关键词
        keywords = [
            f"{celebrity_name} 演技",
            f"{celebrity_name} 电影",
            f"{celebrity_name} 评价"
        ]

        for keyword in keywords:
            topics = await self.search_group_topics(keyword, count=5)
            discussions.extend([{
                "keyword": keyword,
                "topics": [t.content for t in topics],
                "count": len(topics)
            }])

            await asyncio.sleep(1)

        return discussions

    async def search_gossip_groups(self, celebrity_name: str) -> list[SocialMediaPost]:
        """搜索八卦小组讨论"""
        # 豆瓣知名八卦小组
        gossip_groups = [
            "吃瓜",
            "娱乐圈八卦",
            "豆瓣鹅组",
            "八组"
        ]

        all_topics = []

        for group_keyword in gossip_groups:
            keyword = f"{celebrity_name} {group_keyword}"
            topics = await self.search_group_topics(keyword, count=3)
            all_topics.extend(topics)

            await asyncio.sleep(1)

            if len(all_topics) >= 15:
                break

        return all_topics[:15]

    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
