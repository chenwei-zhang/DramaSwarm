"""
微博深度爬虫 - 基于 weibo-spider 包的安全封装
使用 weibo.cn (移动网页版) 爬取用户资料和微博动态
"""

from __future__ import annotations

import logging
import re
import sys
import time
import random
from datetime import datetime, timedelta
from typing import Optional

from ..models import CelebrityProfile, SocialMediaPost

logger = logging.getLogger(__name__)


def _safe_handle_html(cookie: str, url: str):
    """安全的 HTML 请求，基于 weibo-spider 的 handle_html 但去掉 sys.exit"""
    import requests
    from lxml import etree

    user_agent = (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    headers = {'User_Agent': user_agent, 'Cookie': cookie}
    resp = requests.get(url, headers=headers, timeout=15)
    return etree.HTML(resp.content)


def _handle_garbled(info) -> str:
    """处理 lxml 元素的乱码文本"""
    try:
        text = info.xpath('string(.)').replace('\u200b', '')
        return text
    except Exception:
        return ''


def _string_to_int(s: str) -> int:
    """字符串数字转整数（支持万、亿）"""
    if isinstance(s, int):
        return s
    s = str(s).strip()
    if not s:
        return 0
    if s.endswith('万+'):
        return int(float(s[:-2]) * 10000)
    elif s.endswith('万'):
        return int(float(s[:-1]) * 10000)
    elif s.endswith('亿'):
        return int(float(s[:-1]) * 100000000)
    try:
        return int(s)
    except ValueError:
        return 0


class WeiboDeepSpider:
    """基于 weibo-spider 包的安全微博爬虫"""

    def __init__(self, cookie: str):
        self.cookie = cookie

    def validate_cookie(self) -> bool:
        """验证 cookie 是否有效"""
        try:
            selector = _safe_handle_html(self.cookie, 'https://weibo.cn/')
            if selector is None:
                return False
            title = selector.xpath('//title/text()')
            if title:
                title_text = title[0]
                # cookie 无效时标题包含"登录"
                if '登录' in title_text:
                    return False
            return True
        except Exception as e:
            logger.error(f"验证 cookie 失败: {e}")
            return False

    def get_user_profile(self, user_uri: str) -> Optional[dict]:
        """
        获取用户资料

        Args:
            user_uri: 微博用户 ID 或个性域名

        Returns:
            用户资料字典，失败返回 None
        """
        try:
            # 1. 获取首页解析真实 UID 和微博数/关注/粉丝
            index_url = f'https://weibo.cn/{user_uri}/profile'
            selector = _safe_handle_html(self.cookie, index_url)
            if selector is None:
                return None

            # 解析真实 user_id
            user_id = user_uri
            url_list = selector.xpath("//div[@class='u']//a")
            for url_el in url_list:
                if (url_el.xpath('string(.)')) == '资料':
                    href_list = url_el.xpath('@href')
                    if href_list and href_list[0].endswith('/info'):
                        user_id = href_list[0][1:-5]
                        break

            # 解析微博数、关注数、粉丝数
            user_info = selector.xpath("//div[@class='tip2']/*/text()")
            weibo_num = 0
            following = 0
            followers = 0
            if len(user_info) >= 3:
                weibo_num = _string_to_int(user_info[0][3:-1])
                following = _string_to_int(user_info[1][3:-1])
                followers = _string_to_int(user_info[2][3:-1])

            # 2. 获取用户详细信息页
            info_url = f'https://weibo.cn/{user_id}/info'
            info_selector = _safe_handle_html(self.cookie, info_url)
            if info_selector is None:
                return None

            # 检查 cookie 有效性
            nickname_el = info_selector.xpath('//title/text()')
            if nickname_el:
                nickname_text = nickname_el[0]
                if '登录' in nickname_text:
                    logger.error('Cookie 无效或已过期')
                    return None

            nickname = nickname_el[0][:-3] if nickname_el else ''

            # 解析基本信息
            profile = {
                'id': user_id,
                'nickname': nickname,
                'weibo_num': weibo_num,
                'following': following,
                'followers': followers,
                'gender': '',
                'location': '',
                'birthday': '',
                'description': '',
                'verified_reason': '',
                'talent': '',
                'education': '',
                'work': '',
            }

            basic_info = info_selector.xpath("//div[@class='c'][3]/text()")
            zh_keys = ['性别', '地区', '生日', '简介', '认证', '达人']
            en_keys = ['gender', 'location', 'birthday', 'description',
                       'verified_reason', 'talent']
            for info_text in basic_info:
                key = info_text.split(':', 1)[0]
                if key in zh_keys:
                    idx = zh_keys.index(key)
                    value = info_text.split(':', 1)[1].replace('\u3000', '')
                    profile[en_keys[idx]] = value

            # 学习/工作经历
            experienced = info_selector.xpath("//div[@class='tip'][2]/text()")
            if experienced and experienced[0] == '学习经历':
                edu_items = info_selector.xpath("//div[@class='c'][4]/text()")
                if edu_items:
                    profile['education'] = edu_items[0][1:].replace('\xa0', ' ')
                work_tip = info_selector.xpath("//div[@class='tip'][3]/text()")
                if work_tip and work_tip[0] == '工作经历':
                    work_items = info_selector.xpath("//div[@class='c'][5]/text()")
                    if work_items:
                        profile['work'] = work_items[0][1:].replace('\xa0', ' ')
            elif experienced and experienced[0] == '工作经历':
                work_items = info_selector.xpath("//div[@class='c'][4]/text()")
                if work_items:
                    profile['work'] = work_items[0][1:].replace('\xa0', ' ')

            logger.info(f"获取用户资料成功: {nickname} (UID: {user_id}, 粉丝: {followers})")
            return profile

        except Exception as e:
            logger.error(f"获取用户资料失败 {user_uri}: {e}")
            return None

    def get_user_posts(self, user_uri: str, page_count: int = 5) -> list[dict]:
        """
        获取用户微博动态

        Args:
            user_uri: 微博用户 ID
            page_count: 爬取页数

        Returns:
            微博列表，每条为字典
        """
        all_posts = []

        for page in range(1, page_count + 1):
            try:
                url = f'https://weibo.cn/{user_uri}/profile?page={page}'
                selector = _safe_handle_html(self.cookie, url)
                if selector is None:
                    break

                info_list = selector.xpath("//div[@class='c']")
                if not info_list:
                    break

                # 检查是否有内容
                has_content = info_list[0].xpath("div/span[@class='ctt']")
                if not has_content:
                    break

                for info in info_list[:-1]:  # 最后一项通常是分页
                    post = self._parse_one_weibo(info)
                    if post:
                        all_posts.append(post)

                logger.info(f"  第 {page} 页获取 {len(info_list) - 1} 条微博")

                # 随机延迟避免被封
                if page < page_count:
                    delay = random.uniform(2, 5)
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"  第 {page} 页爬取失败: {e}")
                break

        return all_posts

    def _parse_one_weibo(self, info) -> Optional[dict]:
        """解析单条微博，基于 PageParser.get_one_weibo"""
        try:
            weibo_id_list = info.xpath('@id')
            if not weibo_id_list:
                return None
            weibo_id = weibo_id_list[0][2:]  # 去掉 "M_" 前缀

            # 是否原创
            is_original = self._is_original(info)

            # 微博内容
            content = self._get_weibo_content(info, is_original, weibo_id)
            if not content or content.strip() == '':
                return None

            # 图片
            pictures = self._get_picture_urls(info, weibo_id)

            # 视频
            video_url = self._get_video_url(info, weibo_id)

            # 发布位置
            publish_place = self._get_publish_place(info)

            # 发布时间
            publish_time = self._get_publish_time(info)

            # 发布工具
            publish_tool = self._get_publish_tool(info)

            # 互动数据
            footer = self._get_weibo_footer(info)

            return {
                'id': weibo_id,
                'content': content,
                'original': is_original,
                'pictures': pictures,
                'video_url': video_url,
                'publish_place': publish_place,
                'publish_time': publish_time,
                'publish_tool': publish_tool,
                'up_num': footer.get('up_num', 0),
                'retweet_num': footer.get('retweet_num', 0),
                'comment_num': footer.get('comment_num', 0),
                'source_url': f'https://weibo.cn/comment/{weibo_id}',
            }

        except Exception as e:
            logger.debug(f"解析微博失败: {e}")
            return None

    def _is_original(self, info) -> bool:
        """判断是否为原创微博"""
        cmt_list = info.xpath("div/span[@class='cmt']")
        return len(cmt_list) <= 3

    def _get_weibo_content(self, info, is_original: bool, weibo_id: str) -> str:
        """获取微博文本内容"""
        try:
            content = _handle_garbled(info)
            if not content:
                return ''

            if is_original:
                content = content[:content.rfind('赞')]
            else:
                # 转发微博
                colon_pos = content.find(':')
                if colon_pos >= 0:
                    content = content[colon_pos + 1:]
                last_zan = content.rfind('赞')
                if last_zan >= 0:
                    content = content[:last_zan]
                last_zan2 = content.rfind('赞')
                if last_zan2 >= 0:
                    content = content[:last_zan2]

            # 提取话题标签
            content = content.strip()
            return content
        except Exception:
            return ''

    def _get_picture_urls(self, info, weibo_id: str) -> str:
        """获取图片 URL"""
        try:
            a_list = info.xpath('div/a/@href')
            first_pic = f'https://weibo.cn/mblog/pic/{weibo_id}'
            if first_pic in ''.join(a_list):
                # 尝试获取所有图片
                all_pic = f'https://weibo.cn/mblog/picAll/{weibo_id}'
                if all_pic in ''.join(a_list):
                    try:
                        from weibo_spider.parser.mblog_picAll_parser import MblogPicAllParser
                        pic_parser = MblogPicAllParser(self.cookie, weibo_id)
                        preview_list = pic_parser.extract_preview_picture_list()
                        pic_list = [p.replace('/thumb180/', '/large/') for p in preview_list]
                        return ','.join(pic_list)
                    except Exception:
                        pass
                else:
                    for link in info.xpath('div/a'):
                        href_list = link.xpath('@href')
                        if href_list and first_pic in href_list[0]:
                            img_list = link.xpath('img/@src')
                            if img_list:
                                return img_list[0].replace('/wap180/', '/large/')
            return ''
        except Exception:
            return ''

    def _get_video_url(self, info, weibo_id: str) -> str:
        """获取视频 URL"""
        try:
            a_list = info.xpath('./div[1]//a')
            for a in a_list:
                href_list = a.xpath('@href')
                if href_list and 'm.weibo.cn/s/video/show?object_id=' in href_list[0]:
                    try:
                        from weibo_spider.parser.util import to_video_download_url
                        return to_video_download_url(self.cookie, href_list[0])
                    except Exception:
                        return href_list[0]
            return ''
        except Exception:
            return ''

    def _get_publish_place(self, info) -> str:
        """获取发布位置"""
        try:
            div_first = info.xpath('div')[0]
            a_list = div_first.xpath('a')
            for a in a_list:
                href_list = a.xpath('@href')
                text_list = a.xpath('text()')
                if href_list and 'place.weibo.com' in href_list[0]:
                    if text_list and text_list[0] == '显示地图':
                        weibo_a = div_first.xpath("span[@class='ctt']/a")
                        if weibo_a:
                            return _handle_garbled(weibo_a[-1])
            return ''
        except Exception:
            return ''

    def _get_publish_time(self, info) -> str:
        """获取发布时间，自动处理跨年"""
        try:
            str_time_list = info.xpath("div/span[@class='ct']")
            if not str_time_list:
                return ''
            str_time = _handle_garbled(str_time_list[0])
            publish_time = str_time.split('来自')[0].strip()

            now = datetime.now()

            if '刚刚' in publish_time:
                return now.strftime('%Y-%m-%d %H:%M')
            elif '分钟' in publish_time:
                minute = int(re.search(r'(\d+)', publish_time).group(1))
                return (now - timedelta(minutes=minute)).strftime('%Y-%m-%d %H:%M')
            elif '今天' in publish_time:
                today = now.strftime('%Y-%m-%d')
                t = publish_time.replace('今天', '').strip()
                return f'{today} {t}'[:16]
            elif '月' in publish_time:
                # 自动判断年份：如果月份大于当前月份，则为去年
                m = re.search(r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2}:\d{2})', publish_time)
                if m:
                    month = int(m.group(1))
                    if month > now.month:
                        year = now.year - 1
                    else:
                        year = now.year
                    return f'{year}-{month:02d}-{int(m.group(2)):02d} {m.group(3)}'
            else:
                return publish_time[:16]
            return publish_time
        except Exception:
            return ''

    def _get_publish_tool(self, info) -> str:
        """获取发布工具"""
        try:
            str_time_list = info.xpath("div/span[@class='ct']")
            if not str_time_list:
                return ''
            str_time = _handle_garbled(str_time_list[0])
            parts = str_time.split('来自')
            if len(parts) > 1:
                return parts[1].strip()
            return ''
        except Exception:
            return ''

    def _get_weibo_footer(self, info) -> dict:
        """获取点赞/转发/评论数"""
        try:
            footer = {}
            div_last = info.xpath('div')[-1]
            str_footer = _handle_garbled(div_last)
            zan_pos = str_footer.rfind('赞')
            if zan_pos >= 0:
                str_footer = str_footer[zan_pos:]
            nums = re.findall(r'\d+', str_footer)
            if len(nums) >= 3:
                footer['up_num'] = int(nums[0])
                footer['retweet_num'] = int(nums[1])
                footer['comment_num'] = int(nums[2])
            return footer
        except Exception:
            return {}

    def scrape_celebrity(self, name: str, user_uri: str,
                         post_pages: int = 5) -> Optional[dict]:
        """
        爬取单个明星的全部微博数据

        Args:
            name: 明星名
            user_uri: 微博 UID
            post_pages: 微博爬取页数

        Returns:
            包含 profile + posts 的字典
        """
        print(f"  [微博深度爬虫] 爬取 {name} (UID: {user_uri})...")

        # 1. 获取用户资料
        profile = self.get_user_profile(user_uri)
        if not profile:
            print(f"  ✗ 获取用户资料失败")
            return None

        print(f"  ✓ {profile['nickname']} | 粉丝: {profile['followers']:,} | "
              f"微博: {profile['weibo_num']:,}")

        # 2. 获取微博动态
        posts = self.get_user_posts(user_uri, page_count=post_pages)
        print(f"  ✓ 获取 {len(posts)} 条微博动态")

        return {
            'profile': profile,
            'posts': posts,
        }


def convert_to_celebrity_profile(data: dict, name: str) -> CelebrityProfile:
    """将 weibo-spider 数据转换为项目 CelebrityProfile"""
    profile = data['profile']
    return CelebrityProfile(
        name=name,
        weibo_id=profile.get('id', ''),
        weibo_followers=profile.get('followers', 0),
        biography=profile.get('description', ''),
        birth_date=profile.get('birthday', '') or None,
        education=profile.get('education', ''),
        updated_at=datetime.now(),
    )


def convert_to_social_posts(posts: list[dict], author: str) -> list[SocialMediaPost]:
    """将 weibo-spider 微博数据转换为项目 SocialMediaPost 列表"""
    result = []
    for p in posts:
        # 解析图片列表
        pics = p.get('pictures', '')
        images = []
        if pics and pics != '无':
            images = [url.strip() for url in pics.split(',') if url.strip()]

        # 解析视频
        videos = []
        if p.get('video_url') and p['video_url'] != '无':
            videos = [p['video_url']]

        # 从内容中提取话题
        topics = re.findall(r'#([^#]+)#', p.get('content', ''))

        post = SocialMediaPost(
            id=p.get('id', ''),
            platform='weibo',
            author=author,
            content=p.get('content', ''),
            images=images[:9],
            videos=videos,
            likes=p.get('up_num', 0),
            reposts=p.get('retweet_num', 0),
            comments=p.get('comment_num', 0),
            publish_time=p.get('publish_time', ''),
            source_url=p.get('source_url', ''),
            tags=topics,
            topics=topics,
            location=p.get('publish_place', ''),
        )
        result.append(post)
    return result
