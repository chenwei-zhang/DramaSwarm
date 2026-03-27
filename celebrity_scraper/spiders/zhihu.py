"""
知乎爬虫 - 爬取明星相关的问答和讨论
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


class ZhihuSpider:
    """知乎爬虫"""

    BASE_URL = "https://www.zhihu.com"
    API_URL = "https://www.zhihu.com/api/v4"

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=2.0, max_delay=4.0, requests_per_minute=15)
        self.ua_rotator = UserAgentRotator()
        self.client = None

    async def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None or self.client.is_closed:
            headers = self.ua_rotator.get_headers()
            headers.update({
                "Referer": "https://www.zhihu.com",
                "X-Requested-With": "XMLHttpRequest"
            })

            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                verify=False
            )

        return self.client

    async def search_questions(self, keyword: str, count: int = 20) -> list[dict]:
        """搜索相关问题"""
        await self.rate_limiter.acquire()

        questions = []

        try:
            client = await self._get_client()
            url = f"{self.API_URL}/search_v3"

            params = {
                "t": "general",
                "q": keyword,
                "correction": 1,
                "offset": 0,
                "limit": 20
            }

            response = await client.get(url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("paging", {}).get("is_end") is False:
                        for item in data.get("data", []):
                            if item.get("type") == "search_result":
                                obj = item.get("object", {})
                                if obj.get("type") == "question":
                                    questions.append({
                                        "id": obj.get("id"),
                                        "title": obj.get("title"),
                                        "excerpt": obj.get("excerpt", ""),
                                        "answer_count": obj.get("answer_count", 0),
                                        "follower_count": obj.get("follower_count", 0)
                                    })

                                    if len(questions) >= count:
                                        break
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"知乎搜索失败 {keyword}: {e}")

        return questions

    async def scrape_answers(self, question_id: str, count: int = 10) -> list[SocialMediaPost]:
        """爬取问题的热门回答"""
        await self.rate_limiter.acquire()

        answers = []

        try:
            client = await self._get_client()
            url = f"{self.API_URL}/questions/{question_id}/answers"

            params = {
                "order_by": "hotness",  # 按热度排序
                "limit": 20,
                "offset": 0
            }

            response = await client.get(url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    for item in data.get("data", []):
                        answer = self._parse_answer(item, question_id)
                        if answer:
                            answers.append(answer)

                        if len(answers) >= count:
                            break
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"爬取回答失败 {question_id}: {e}")

        return answers

    async def scrape_comments(self, answer_id: str, count: int = 30) -> list[Comment]:
        """爬取回答评论"""
        await self.rate_limiter.acquire()

        comments = []

        try:
            client = await self._get_client()
            url = f"{self.API_URL}/answers/{answer_id}/root_comments"

            params = {
                "order_by": "hotness",  # 热门评论
                "limit": 20,
                "offset": 0
            }

            response = await client.get(url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    for item in data.get("data", []):
                        comment = self._parse_comment(item, "zhihu", answer_id)
                        if comment:
                            comments.append(comment)

                        if len(comments) >= count:
                            break
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"爬取评论失败 {answer_id}: {e}")

        return comments

    def _parse_answer(self, item: dict, question_id: str) -> Optional[SocialMediaPost]:
        """解析回答内容"""
        try:
            author = item.get("author", {})
            content = item.get("content", "")

            # 清理HTML标签
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text()

                # 提取图片
                images = [img.get("src", "") for img in soup.find_all("img") if img.get("src")]

            # 提取话题标签
            excerpt = item.get("excerpt", "")
            tags = re.findall(r'#([^#\s]+)#', excerpt + text)

            return SocialMediaPost(
                id=str(item.get("id", "")),
                platform="zhihu",
                author=author.get("name", "匿名用户"),
                author_id=str(author.get("id", "")),
                content=text[:2000],  # 限制长度
                images=images[:5],  # 限制图片数量
                likes=item.get("voteup_count", 0),
                comments=item.get("comment_count", 0),
                reposts=0,
                publish_time=item.get("created_time"),
                source_url=f"{self.BASE_URL}/question/{question_id}/answer/{item.get('id')}",
                tags=tags[:10]
            )
        except Exception as e:
            print(f"解析回答失败: {e}")
            return None

    def _parse_comment(self, item: dict, platform: str, answer_id: str) -> Optional[Comment]:
        """解析评论"""
        try:
            author = item.get("author", {})
            content = item.get("content", "")

            # 清理HTML
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text()

            return Comment(
                id=str(item.get("id", "")),
                content=content,
                author=author.get("name", "匿名用户"),
                author_id=str(author.get("id", "")),
                likes=item.get("vote_count", 0),
                replies=item.get("child_comment_count", 0),
                is_top=item.get("is_author", False),
                publish_time=item.get("created_time"),
                source_platform=platform,
                source_url=f"{self.BASE_URL}/answer/{answer_id}"
            )
        except Exception as e:
            print(f"解析评论失败: {e}")
            return None

    async def search_celebrity_topic(self, celebrity_name: str) -> dict:
        """搜索明星相关话题和讨论"""
        result = {
            "questions": [],
            "hot_discussions": [],
            "gossip_keywords": []
        }

        # 搜索八卦相关关键词
        gossip_keywords = [
            f"{celebrity_name} 八卦",
            f"{celebrity_name} 绯闻",
            f"{celebrity_name} 争议",
            f"{celebrity_name} 私生活"
        ]

        for keyword in gossip_keywords:
            questions = await self.search_questions(keyword, count=5)
            result["questions"].extend(questions)

            if questions:
                result["gossip_keywords"].append(keyword)

            await asyncio.sleep(1)

        # 去重
        seen = set()
        unique_questions = []
        for q in result["questions"]:
            if q["id"] not in seen:
                seen.add(q["id"])
                unique_questions.append(q)

        result["questions"] = unique_questions[:20]

        return result

    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
