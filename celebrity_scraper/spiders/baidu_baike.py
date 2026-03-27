"""
百度百科爬虫 - 爬取明星的基本信息
"""

from __future__ import annotations

import asyncio
import re
from bs4 import BeautifulSoup
from typing import Optional
import httpx

from ..models import CelebrityProfile, GossipItem, Relationship, ScrapeResult, DataSourceType
from ..utils import RateLimiter, UserAgentRotator


class BaiduBaikeSpider:
    """百度百科爬虫"""

    BASE_URL = "https://baike.baidu.com"

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=2.0, max_delay=5.0, requests_per_minute=15)
        self.ua_rotator = UserAgentRotator()
        self.client = None

    async def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None or self.client.is_closed:
            headers = self.ua_rotator.get_headers()
            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                verify=False
            )
        return self.client

    async def search_celebrity(self, name: str) -> Optional[str]:
        """搜索明星，获取百度百科URL"""
        await self.rate_limiter.acquire()

        try:
            client = await self._get_client()
            search_url = f"https://baike.baidu.com/item/{name}"
            response = await client.get(search_url)

            if response.status_code == 200:
                if "百度百科" in response.text and "百度百科尚未收录词条" not in response.text:
                    return str(response.url)

            return None

        except Exception as e:
            print(f"搜索失败 {name}: {e}")
            return None

    async def scrape_celebrity(self, name: str) -> ScrapeResult:
        """爬取明星信息"""
        print(f"正在爬取: {name}")

        profile = CelebrityProfile(name=name)
        gossips = []
        relationships = []

        url = await self.search_celebrity(name)

        if not url:
            print(f"未找到 {name} 的百度百科页面")
            return ScrapeResult(celebrity=profile)

        await self.rate_limiter.acquire()

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code != 200:
                return ScrapeResult(celebrity=profile)

            soup = BeautifulSoup(response.text, 'html.parser')

            # 从meta标签解析 - 最可靠的方式
            self._parse_meta_info(soup, profile)

            # 解析主要内容
            self._parse_main_content(soup, profile)

            # 从简介中提取关系
            if profile.biography:
                self._parse_relationships_from_text(profile, relationships)

            # 标记职业
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                for job in ['演员', '歌手', '主持人', '模特', '导演', '说唱歌手', '艺人']:
                    if job in title_text and job not in profile.occupation:
                        profile.occupation.append(job)

            profile.sources.append(url)
            print(f"✓ 完成爬取: {name} - {', '.join(profile.occupation)}")

        except Exception as e:
            print(f"爬取错误 {name}: {e}")

        return ScrapeResult(
            celebrity=profile,
            gossips=gossips,
            relationships=relationships
        )

    def _parse_meta_info(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """从meta标签解析基本信息"""
        # 从description获取简介
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta and desc_meta.get('content'):
            profile.biography = desc_meta['content']

        # 从keywords提取标签
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta and keywords_meta.get('content'):
            keywords = keywords_meta['content'].split(',')
            # 过滤出职业
            for kw in keywords:
                kw = kw.strip()
                if any(job in kw for job in ['演员', '歌手', '主持人', '模特', '导演']):
                    if kw not in profile.occupation:
                        profile.occupation.append(kw)

    def _parse_main_content(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """解析主要内容区域"""
        # 从简介文本中提取基本信息
        if profile.biography:
            text = profile.biography
            self._extract_info_from_text(text, profile)

    def _extract_info_from_text(self, text: str, profile: CelebrityProfile):
        """从文本中提取信息"""
        # 出生日期
        birth_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        matches = re.findall(birth_pattern, text)
        if matches and not profile.birth_date:
            profile.birth_date = f"{matches[0][0]}-{matches[0][1]}-{matches[0][2]}"

        # 出生地
        if '出生于' in text or '生于' in text:
            place_pattern = r'出生于\s*([^，。]{2,15})|生于\s*([^，。]{2,15})'
            match = re.search(place_pattern, text)
            if match:
                profile.birth_place = match.group(1) or match.group(2)

        # 经纪公司
        if '经纪公司' in text:
            company_match = re.search(r'经纪公司[为是：:]\s*([^，。]{2,30})', text)
            if company_match:
                profile.company = company_match.group(1)

    def _parse_relationships_from_text(self, profile: CelebrityProfile, relationships: list):
        """从文本中解析关系"""
        if not profile.biography:
            return

        text = profile.biography

        # 常见关系模式
        relation_patterns = [
            (r'配偶[：:]\s*([^，。]{2,10})', '配偶'),
            (r'妻子[是为]\s*([^，。]{2,10})', '妻子'),
            (r'丈夫[是为]\s*([^，。]{2,10})', '丈夫'),
            (r'前妻[：:]\s*([^，。]{2,10})', '前妻'),
            (r'前夫[：:]\s*([^，。]{2,10})', '前夫'),
            (r'男友[：:]\s*([^，。]{2,10})', '男友'),
            (r'女友[：:]\s*([^，。]{2,10})', '女友'),
            (r'搭档[：:]\s*([^，。]{2,10})', '搭档'),
        ]

        for pattern, rel_type in relation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                related_name = match.group(1).strip()
                if len(related_name) >= 2 and related_name != profile.name:
                    # 避免重复
                    existing = any(
                        r.person_b == related_name and r.relation_type == rel_type
                        for r in relationships
                    )
                    if not existing:
                        relationships.append(Relationship(
                            person_a=profile.name,
                            person_b=related_name,
                            relation_type=rel_type,
                            confidence=0.7
                        ))

    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
