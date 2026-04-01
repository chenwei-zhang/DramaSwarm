"""
百度百科爬虫 - 爬取明星的基本信息
"""

from __future__ import annotations

import asyncio
import re
import json
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin, quote
import httpx

from ..models import (
    CelebrityProfile, GossipItem, Relationship, ScrapeResult,
    DataSourceType, GossipType
)
from ..utils import RateLimiter, UserAgentRotator


class BaiduBaikeSpider:
    """百度百科爬虫"""

    BASE_URL = "https://baike.baidu.com"
    ITEM_URL = "https://baike.baidu.com/item"
    SEARCH_URL = "https://baike.baidu.com/search"

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=1.5, max_delay=4.0, requests_per_minute=15)
        self.ua_rotator = UserAgentRotator()
        self.client = None
        self.session_cookies = {}

    async def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None or self.client.is_closed:
            headers = self.ua_rotator.get_headers()
            headers.update({
                "Referer": "https://baike.baidu.com",
                "Origin": "https://baike.baidu.com",
            })

            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
                verify=False,
                cookies=self.session_cookies
            )

        return self.client

    async def search_celebrity(self, name: str) -> Optional[str]:
        """搜索明星，获取百度百科URL"""
        await self.rate_limiter.acquire()

        try:
            client = await self._get_client()

            # 方法1: 尝试直接访问（URL编码）
            encoded_name = quote(name)
            direct_urls = [
                f"{self.ITEM_URL}/{encoded_name}",
                f"{self.ITEM_URL}?title={encoded_name}",
            ]

            for url in direct_urls:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        # 检查是否是有效页面
                        if self._is_valid_baike_page(response.text):
                            print(f"  ✓ 找到百科页面: {name}")
                            # 保存cookies
                            if response.cookies:
                                self.session_cookies.update(dict(response.cookies))
                            return str(response.url)
                except Exception:
                    continue

            # 方法2: 使用搜索功能
            try:
                search_params = {
                    "word": name,
                    "type": 0,
                    "limit": 10
                }
                response = await client.get(self.SEARCH_URL, params=search_params, follow_redirects=True)

                if response.status_code == 200:
                    search_url = str(response.url)
                    # 尝试从搜索结果页解析
                    item_url = self._parse_search_results(response.text, name)
                    if item_url:
                        print(f"  ✓ 搜索找到百科页面: {name}")
                        return urljoin(self.BASE_URL, item_url)

            except Exception as e:
                print(f"  搜索请求失败: {e}")

            print(f"  ✗ 未找到百科页面: {name}")
            return None

        except Exception as e:
            print(f"  搜索失败 {name}: {e}")
            return None

    def _is_valid_baike_page(self, html: str) -> bool:
        """检查是否是有效的百科页面"""
        # 有效指标优先判断
        valid_indicators = [
            "basicInfo-item",
            "lemma-summary",
            "view-more-pic",
            "lemmaTitle",
        ]
        has_valid = any(indicator in html for indicator in valid_indicators)
        if not has_valid:
            return False

        # 排除明确的错误页面
        invalid_indicators = [
            "百度百科尚未收录词条",
            "抱歉，您访问的页面不存在",
            "词条已锁定",
            "抱歉，没有找到与",
        ]
        for indicator in invalid_indicators:
            if indicator in html:
                return False

        return True

    def _parse_search_results(self, html: str, name: str) -> Optional[str]:
        """从搜索结果页解析条目链接"""
        soup = BeautifulSoup(html, 'html.parser')

        # 各种可能的搜索结果选择器
        selectors = [
            'a[href*="/item/"]',
            '.search-result-item a.title',
            '.item a',
            'dd a[class*="title"]',
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                title = link.get_text(strip=True)

                # 匹配名字或者URL包含名字
                if name in title or name in href:
                    if '/item/' in href:
                        return href

        return None

    async def scrape_celebrity(self, name: str) -> ScrapeResult:
        """爬取明星信息"""
        print(f"  正在爬取百科: {name}")

        profile = CelebrityProfile(name=name)
        gossips = []
        relationships = []

        url = await self.search_celebrity(name)

        if not url:
            return ScrapeResult(celebrity=profile)

        await self.rate_limiter.acquire()

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code != 200:
                return ScrapeResult(celebrity=profile)

            soup = BeautifulSoup(response.text, 'html.parser')

            # 解析基本信息
            self._parse_basic_info(soup, profile)

            # 解析简介
            self._parse_summary(soup, profile)

            # 解析详细信息块
            self._parse_info_items(soup, profile)

            # 解析职业生涯/作品
            self._parse_career(soup, profile)

            # 解析人物关系
            self._parse_relationships(soup, profile, relationships)

            # 解析八卦/争议（如果有专门章节）
            self._parse_gossip_section(soup, profile, gossips)

            # 获取头像
            self._parse_avatar(soup, profile)

            # 从标题补充职业
            self._parse_title_for_occupation(soup, profile)

            profile.sources.append(url)
            print(f"  ✓ 完成百科爬取: {name} - {', '.join(profile.occupation) if profile.occupation else '资料'}")

        except Exception as e:
            print(f"  ✗ 爬取错误 {name}: {e}")

        return ScrapeResult(
            celebrity=profile,
            gossips=gossips,
            relationships=relationships
        )

    def _parse_basic_info(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """解析基本信息"""
        # 从meta标签获取
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta:
            content = desc_meta.get('content', '')
            if content:
                profile.biography = content

        # 从keywords提取标签
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta:
            keywords = keywords_meta.get('content', '')
            if keywords:
                profile.raw_data['keywords'] = [k.strip() for k in keywords.split(',') if k.strip()]

    def _parse_summary(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """解析简介"""
        # 多种可能的选择器
        summary_selectors = [
            '.lemma-summary',
            '.summary',
            '#lemma-summary',
            '.encyclopedia-summary',
            '.bk_polysemous-entity-summary',
        ]

        for selector in summary_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator='\n', strip=True)
                # 清理文本
                text = re.sub(r'\n\s*\n', '\n', text)
                text = text[:1000]  # 限制长度
                if text and len(text) > 10:
                    profile.biography = text
                    break

    def _parse_info_items(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """解析详细信息块（出生日期、身高、体重等）"""
        # 基本信息容器
        info_containers = [
            soup.select('.basicInfo-item'),
            soup.select('.info-item'),
            soup.select('.bk-info-item'),
            soup.select('table.infobox tr'),
        ]

        for items in info_containers:
            if not items:
                continue

            for item in items:
                try:
                    # 获取标签名和值
                    label_elem = item.select_one('.name') or item.select_one('th') or item.select_one('.label')
                    value_elem = item.select_one('.value') or item.select_one('td') or item.select_one('.content')

                    if not label_elem or not value_elem:
                        continue

                    label = label_elem.get_text(strip=True).rstrip('：')
                    value = value_elem.get_text(strip=True)

                    self._assign_info_to_profile(label, value, profile)

                except Exception:
                    continue

    def _assign_info_to_profile(self, label: str, value: str, profile: CelebrityProfile):
        """根据标签名分配信息到对应字段"""
        label_lower = label.lower()

        # 中文名映射
        field_mapping = {
            '中文名': 'name',
            '外文名': 'english_name',
            '英文名': 'english_name',
            '国籍': 'nationality',
            '民族': 'ethnicity',
            '出生': 'birth_date',
            '出生日期': 'birth_date',
            '出生地': 'birth_place',
            '出生地点': 'birth_place',
            '身高': 'height',
            '体重': 'weight',
            '血型': 'blood_type',
            '星座': 'constellation',
            '生肖': 'zodiac',
            '职业': 'occupation',
            '毕业院校': 'alma_mater',
            '经纪公司': 'company',
            '代表作品': 'famous_works',
            '主要成就': 'achievements',
        }

        # 根据标签处理
        if '出生' in label:
            # 从出生信息提取日期和地点
            birth_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', value)
            if birth_match:
                profile.birth_date = f"{birth_match.group(1)}-{birth_match.group(2)}-{birth_match.group(3)}"

            place_match = re.search(r'([^，。\s]{2,10}(?:省|市|区|县|国))', value)
            if place_match:
                profile.birth_place = place_match.group(1)

        elif '身' in label and '高' in label:
            profile.height = value

        elif '体重' in label:
            profile.weight = value

        elif '星座' in label:
            profile.constellation = value

        elif '生肖' in label:
            profile.zodiac = value

        elif '血型' in label:
            profile.blood_type = value

        elif '毕业院校' in label or '母校' in label:
            profile.alma_mater = value
            profile.education = value

        elif '经纪公司' in label:
            profile.company = value

        elif '职业' in label or '身份' in label:
            occupations = [v.strip() for v in value.split('、') if v.strip()]
            profile.occupation.extend(occupations)

        elif '代表作品' in label or '主要作品' in label:
            works = [w.strip() for w in value.split('、') if w.strip()]
            profile.famous_works.extend(works[:20])

        elif '英文名' in label or '外文名' in label:
            if not profile.english_name:
                profile.english_name = value

    def _parse_career(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """解析职业生涯/作品"""
        # 查找作品列表
        career_selectors = [
            'h2:contains("演艺经历") + .para',
            'h2:contains("作品") + .para',
            '.career-list',
            '.works-list',
        ]

        works_found = []
        for selector in career_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                # 提取作品名
                work_matches = re.findall(r'《([^》]+)》', text)
                works_found.extend(work_matches)

        if works_found and not profile.famous_works:
            profile.famous_works = list(set(works_found))[:20]

    @staticmethod
    def _is_valid_person_name(text: str) -> bool:
        """判断是否像中国人名（2-4个纯中文字符）"""
        text = text.strip()
        if not (2 <= len(text) <= 4):
            return False
        return bool(re.fullmatch(r'[\u4e00-\u9fff]{2,4}', text))

    def _parse_relationships(self, soup: BeautifulSoup, profile: CelebrityProfile, relationships: list):
        """解析人物关系（仅从简介中提取，严格校验人名格式）"""
        text = profile.biography or ""

        # 关系模式 — 只匹配紧贴关键词后的纯中文名
        relation_patterns = [
            (r'(?:配偶|丈夫|老公|妻子|老婆)[是为]\s*([\u4e00-\u9fff]{2,4})', '配偶'),
            (r'(?:前夫|前妻|前男友|前女友)[是为]\s*([\u4e00-\u9fff]{2,4})', '前任'),
            (r'(?:男友|女朋友|女朋友)[是为]\s*([\u4e00-\u9fff]{2,4})', '恋人'),
            (r'(?:绯闻男友|绯闻女友|绯闻对象)[是为]\s*([\u4e00-\u9fff]{2,4})', '绯闻'),
            (r'(?:搭档|合作)[是为]\s*([\u4e00-\u9fff]{2,4})', '搭档'),
            (r'(?:好友|闺蜜)[是为]\s*([\u4e00-\u9fff]{2,4})', '朋友'),
            (r'(?:儿女|儿子|女儿)[是为]\s*([\u4e00-\u9fff]{2,4})', '子女'),
        ]

        for pattern, rel_type in relation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                related_name = match.group(1).strip()
                if self._is_valid_person_name(related_name) and related_name != profile.name:
                    existing = any(
                        r.person_b == related_name and r.relation_type == rel_type
                        for r in relationships
                    )
                    if not existing:
                        relationships.append(Relationship(
                            person_a=profile.name,
                            person_b=related_name,
                            relation_type=rel_type,
                            confidence=0.75,
                            description=f"从百度百科提取"
                        ))

    def _parse_gossip_section(self, soup: BeautifulSoup, profile: CelebrityProfile, gossips: list):
        """解析八卦/争议章节"""
        # 查找可能包含八卦的章节
        gossip_keywords = ['争议', '事件', '绯闻', '八卦', '丑闻']

        for keyword in gossip_keywords:
            headers = soup.find_all(['h2', 'h3'], string=re.compile(keyword))
            for header in headers:
                # 获取该章节的内容
                content = []
                sibling = header.find_next_sibling()
                while sibling and sibling.name not in ['h1', 'h2', 'h3']:
                    content.append(sibling.get_text(strip=True))
                    sibling = sibling.find_next_sibling()

                if content:
                    full_text = ' '.join(content)
                    if len(full_text) > 20:
                        # 判断八卦类型
                        gossip_type = GossipType.OTHER
                        if '恋情' in full_text or '结婚' in full_text:
                            gossip_type = GossipType.ROMANCE
                        elif '离婚' in full_text:
                            gossip_type = GossipType.DIVORCE
                        elif '出轨' in full_text or '丑闻' in full_text:
                            gossip_type = GossipType.CHEATING

                        gossips.append(GossipItem(
                            title=f"{keyword}相关",
                            content=full_text[:500],
                            gossip_type=gossip_type,
                            source_type=DataSourceType.BAIDU_BAIKE,
                            verified=True
                        ))

    def _parse_avatar(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """解析头像"""
        avatar_selectors = [
            '.summary-pic img',
            '.lemma-pic img',
            '.profile-photo img',
            'img[class*="avatar"]',
        ]

        for selector in avatar_selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    profile.avatar_url = urljoin(self.BASE_URL, src)
                    break

    def _parse_title_for_occupation(self, soup: BeautifulSoup, profile: CelebrityProfile):
        """从页面标题提取职业"""
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text()

            occupations_from_title = []
            job_keywords = ['演员', '歌手', '主持人', '模特', '导演', '制片人',
                          '编剧', '舞者', '说唱歌手', '艺人', '明星']

            for job in job_keywords:
                if job in title_text and job not in profile.occupation:
                    occupations_from_title.append(job)

            profile.occupation.extend(occupations_from_title)

    async def close(self):
        """关闭客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
