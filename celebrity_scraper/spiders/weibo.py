"""
微博爬虫 - 爬取明星动态和评论
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import httpx

from ..models import (
    SocialMediaPost, Comment, CelebrityProfile, DataSourceType,
    GossipItem, GossipType
)
from ..utils import RateLimiter, UserAgentRotator


class WeiboSpider:
    """微博爬虫"""

    BASE_URL = "https://weibo.com"
    MOBILE_URL = "https://m.weibo.cn"
    API_BASE = "https://m.weibo.cn/api"

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=1.2, max_delay=2.5, requests_per_minute=25)
        self.ua_rotator = UserAgentRotator()
        self.client = None
        self.mobile_client = None
        self.cookies = {}

    async def _get_client(self, mobile: bool = False):
        """获取HTTP客户端"""
        target_client = self.mobile_client if mobile else self.client

        if target_client is None or target_client.is_closed:
            headers = self.ua_rotator.get_headers()

            if mobile:
                headers.update({
                    "Referer": "https://m.weibo.cn",
                    "MWeibo-Pwa": "1",
                    "X-Requested-With": "XMLHttpRequest",
                })
            else:
                headers.update({
                    "Referer": "https://weibo.com",
                })

            target_client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                verify=False,
                cookies=self.cookies
            )

            if mobile:
                self.mobile_client = target_client
            else:
                self.client = target_client

        return target_client

    async def search_celebrity(self, name: str) -> Optional[dict]:
        """搜索明星，获取UID和基本信息"""
        await self.rate_limiter.acquire()

        try:
            client = await self._get_client(mobile=True)

            # 使用移动端搜索API
            search_url = f"{self.API_BASE}/container/getIndex"
            params = {
                "containerid": f"100103type=1&q={name}",
                "page_type": "searchall",
                "page": 1
            }

            response = await client.get(search_url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("ok"):
                        cards = data.get("data", {}).get("cards", [])

                        for card in cards:
                            # 用户卡片
                            if card.get("card_type") == 11:
                                card_group = card.get("card_group", [])
                                for item in card_group:
                                    if item.get("card_type") == 10:
                                        user_info = item.get("user", {})
                                        return {
                                            "uid": user_info.get("id"),
                                            "name": user_info.get("screen_name"),
                                            "description": user_info.get("description", ""),
                                            "followers_count": user_info.get("followers_count", 0),
                                            "following_count": user_info.get("follow_count", 0),
                                            "verified": user_info.get("verified", False),
                                            "verified_reason": user_info.get("verified_reason", ""),
                                            "avatar": user_info.get("profile_image_url", ""),
                                        }

                            # 直接的用户结果
                            elif card.get("card_type") == 10:
                                user_info = card.get("user", {})
                                if user_info:
                                    return {
                                        "uid": user_info.get("id"),
                                        "name": user_info.get("screen_name"),
                                        "description": user_info.get("description", ""),
                                        "followers_count": user_info.get("followers_count", 0),
                                        "verified": user_info.get("verified", False),
                                    }

                except json.JSONDecodeError:
                    pass

            return None

        except Exception as e:
            print(f"  微博搜索失败 {name}: {e}")
            return None

    async def scrape_posts(self, uid: str, count: int = 20) -> list[SocialMediaPost]:
        """爬取明星微博"""
        await self.rate_limiter.acquire()

        posts = []
        page = 1

        try:
            client = await self._get_client(mobile=True)

            while len(posts) < count and page <= 5:
                container_id = f"107603{uid}"
                url = f"{self.API_BASE}/container/getIndex"

                params = {
                    "type": "uid",
                    "value": uid,
                    "containerid": container_id,
                    "page": page
                }

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("ok"):
                            cards = data.get("data", {}).get("cards", [])

                            for card in cards:
                                if card.get("card_type") == 9:
                                    mblog = card.get("mblog", {})
                                    post = self._parse_post(mblog)
                                    if post and post.content:
                                        posts.append(post)

                                    if len(posts) >= count:
                                        break

                            # 没有更多数据
                            if not cards:
                                break

                    except json.JSONDecodeError:
                        break
                else:
                    break

                page += 1
                await asyncio.sleep(0.8)

        except Exception as e:
            print(f"  爬取微博动态失败: {e}")

        return posts

    async def scrape_comments(self, post_id: str, count: int = 50) -> list[Comment]:
        """爬取微博评论"""
        await self.rate_limiter.acquire()

        comments = []

        try:
            client = await self._get_client(mobile=True)
            url = f"{self.API_BASE}/container/getIndex"

            max_id = ""
            max_id_type = "0"

            while len(comments) < count:
                params = {
                    "containerid": f"{int(post_id)}_-_WEIBO_SECOND_DETAIL_WEIBO",
                    "open_app": "",
                    "max_id": max_id,
                    "max_id_type": max_id_type,
                    "page_type": "comment"
                }

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("ok"):
                            comment_data = data.get("data", {})
                            new_comments = self._parse_comments(comment_data, post_id)
                            comments.extend(new_comments)

                            # 获取下一页参数
                            max_id = comment_data.get("max_id", "")
                            max_id_type = comment_data.get("max_id_type", "0")

                            if not max_id or len(comments) >= count:
                                break
                        else:
                            break
                    except json.JSONDecodeError:
                        break
                else:
                    break

                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  爬取评论失败: {e}")

        return comments[:count]

    def _parse_post(self, mblog: dict) -> Optional[SocialMediaPost]:
        """解析微博内容"""
        try:
            post_id = mblog.get("id", "")
            text = mblog.get("text", "")

            # 清理HTML标签
            if text:
                soup = BeautifulSoup(text, 'html.parser')
                # 处理表情、话题等
                text = soup.get_text()

            # 提取图片
            images = []
            pic_ids = mblog.get("pic_ids", [])
            pic_infos = mblog.get("pic_infos", {})
            if pic_ids and pic_infos:
                for pid in pic_ids:
                    if pid in pic_infos:
                        largest = pic_infos[pid].get("largest", {})
                        url = largest.get("url", "")
                        if url:
                            images.append(url)

            # 提取视频
            videos = []
            page_info = mblog.get("page_info", {})
            if page_info:
                media_info = page_info.get("media_info", {})
                if media_info:
                    video_url = media_info.get("stream_url", "") or media_info.get("video_url", "")
                    if video_url:
                        videos.append(video_url)

            # 提取话题和标签
            topics = re.findall(r'#([^#]+)#', text)
            hashtags = mblog.get("topics", []) if isinstance(mblog.get("topics"), list) else []

            # 用户信息
            user = mblog.get("user", {})
            author = user.get("screen_name", "")
            author_id = user.get("id", "")
            verified = user.get("verified", False)

            # 是否为转发
            is_repost = mblog.get("retweeted_status") is not None
            repost_from_id = ""
            repost_from_author = ""
            if is_repost:
                retweeted = mblog.get("retweeted_status", {})
                repost_user = retweeted.get("user", {})
                repost_from_id = retweeted.get("id", "")
                repost_from_author = repost_user.get("screen_name", "")

            return SocialMediaPost(
                id=post_id,
                platform="weibo",
                author=author,
                author_id=author_id,
                author_verified=verified,
                content=text,
                images=images[:9],
                videos=videos,
                likes=mblog.get("attitudes_count", 0),
                reposts=mblog.get("reposts_count", 0),
                comments=mblog.get("comments_count", 0),
                publish_time=mblog.get("created_at"),
                publish_timestamp=mblog.get("created_timestamp", 0),
                source_url=f"{self.MOBILE_URL}/status/{post_id}",
                tags=topics,
                hashtags=hashtags,
                topics=topics,
                is_ad=mblog.get("is_ad", False),
                repost_from_id=repost_from_id,
                repost_from_author=repost_from_author
            )
        except Exception as e:
            return None

    def _parse_comments(self, comment_data: dict, post_id: str) -> list[Comment]:
        """解析评论数据"""
        comments = []

        try:
            comments_list = comment_data.get("data", [])

            for item in comments_list:
                # 主评论
                comment = self._parse_single_comment(item, post_id)
                if comment:
                    comments.append(comment)

                # 子评论
                sub_comments = item.get("comments", [])
                for sub_item in sub_comments:
                    sub_comment = self._parse_single_comment(sub_item, post_id, parent_id=comment.id if comment else "")
                    if sub_comment:
                        comments.append(sub_comment)

        except Exception as e:
            pass

        return comments

    def _parse_single_comment(self, item: dict, post_id: str, parent_id: str = "") -> Optional[Comment]:
        """解析单条评论"""
        try:
            user = item.get("user", {})
            text = item.get("text", "")

            # 清理HTML
            if text:
                soup = BeautifulSoup(text, 'html.parser')
                text = soup.get_text()

            return Comment(
                id=str(item.get("id", "")),
                content=text,
                author=user.get("screen_name", ""),
                author_id=user.get("idstr", ""),
                is_author_verified=user.get("verified", False),
                likes=item.get("like_count", 0),
                replies=len(item.get("comments", [])),
                is_top=item.get("is_top", False),
                publish_time=item.get("created_at"),
                source_platform="weibo",
                source_url=f"{self.MOBILE_URL}/status/{post_id}",
                parent_id=parent_id,
                reply_to_id=str(item.get("reply_id", "")),
                reply_to_name=item.get("reply_name", "")
            )
        except Exception:
            return None

    async def search_gossip(self, keyword: str, count: int = 30) -> list[SocialMediaPost]:
        """搜索八卦相关微博"""
        await self.rate_limiter.acquire()

        posts = []

        try:
            client = await self._get_client(mobile=True)
            url = f"{self.API_BASE}/container/getIndex"

            params = {
                "containerid": f"100103type=1&q={keyword}",
                "page_type": "searchall"
            }

            response = await client.get(url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("ok"):
                        cards = data.get("data", {}).get("cards", [])

                        for card in cards:
                            # 搜索结果中的微博
                            if card.get("card_type") == 9:
                                mblog = card.get("mblog", {})
                                post = self._parse_post(mblog)
                                if post and post.content:
                                    posts.append(post)

                            if len(posts) >= count:
                                break

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"  搜索八卦失败: {e}")

        return posts

    async def get_hot_search(self, category: str = "ent") -> list[dict]:
        """获取热搜榜"""
        await self.rate_limiter.acquire()

        hot_items = []

        try:
            client = await self._get_client(mobile=True)
            url = f"{self.API_BASE}/container/getIndex"

            # 娱乐热搜
            container_id = "106003type=25&t=3&disable_hot=1&containerid=106003type=25"
            if category == "ent":
                container_id = "102803"

            params = {
                "containerid": container_id,
            }

            response = await client.get(url, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("ok"):
                        cards = data.get("data", {}).get("cards", [])
                        for card in cards:
                            card_group = card.get("card_group", [])
                            for item in card_group:
                                title = item.get("title_desc", "") or item.get("title", "")
                                rank = item.get("rank", 0)
                                hot = item.get("desc", "")

                                if title:
                                    hot_items.append({
                                        "title": title,
                                        "rank": rank,
                                        "heat": hot,
                                        "category": category
                                    })

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"  获取热搜失败: {e}")

        return hot_items

    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
        if self.mobile_client and not self.mobile_client.is_closed:
            await self.mobile_client.aclose()
