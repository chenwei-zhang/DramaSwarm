"""
明星爬虫主程序 - 协调多个爬虫
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Callable

from .spiders import (
    BaiduBaikeSpider,
    WeiboSpider,
    WeiboDeepSpider,
    ZhihuSpider,
    DoubanSpider,
    EntertainmentNewsSpider
)
from .spiders.weibo_deep_spider import convert_to_celebrity_profile, convert_to_social_posts
from .models import (
    CelebrityProfile, ScrapeResult, NewsArticle, Comment,
    SocialMediaPost, GossipItem, GossipType, DataSourceType
)
from .mock_data import generate_mock_result, get_available_celebrities


# 10位中国顶流明星列表
TOP_CELEBRITIES = [
    # 演员/艺人
    "肖战",
    "王一博",
    "杨幂",
    "赵丽颖",
    "迪丽热巴",
    "唐嫣",
    "罗晋",
    "李小璐",
    "贾乃亮",
    "PG One",
]

# 更多明星可扩展
MORE_CELEBRITIES = [
    "Angelababy",
    "黄晓明",
    "范冰冰",
    "李晨",
    "郑恺",
    "吴亦凡",
    "蔡徐坤",
    "张艺兴",
    "易烊千玺",
    "王俊凯",
    "王源",
    "刘亦菲",
    "胡歌",
    "彭于晏",
    "周冬雨",
    "郑爽",
    "张一山",
    "刘诗诗",
    "吴奇隆",
]

# 八卦热门明星
GOSSIP_CELEBRITIES = [
    "李小璐",
    "贾乃亮",
    "PG One",
    "吴亦凡",
    "郑爽",
    "Angelababy",
    "黄晓明",
    "范冰冰",
    "汪峰",
    "章子怡",
]


class CelebrityScraper:
    """明星爬虫主类"""

    def __init__(
        self,
        output_dir: str = "data",
        enable_all_sources: bool = True,
        progress_callback: Callable | None = None,
        mock_mode: bool = False,
        weibo_mode: str = "mock",
        weibo_cookie: str = ""
    ):
        """
        Args:
            weibo_mode: 微博爬取模式
                - "mock": 使用模拟数据
                - "api": 使用移动端 API（无需 cookie，数据有限）
                - "deep": 使用 weibo-spider 深度爬取（需要 cookie）
            weibo_cookie: 微博 cookie，weibo_mode="deep" 时必需
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.enable_all_sources = enable_all_sources
        self.progress_callback = progress_callback
        self.mock_mode = mock_mode
        self.weibo_mode = weibo_mode
        self.weibo_cookie = weibo_cookie

        # 初始化所有爬虫
        self.baike_spider = BaiduBaikeSpider()
        self.weibo_spider = WeiboSpider()
        self.zhihu_spider = ZhihuSpider()
        self.douban_spider = DoubanSpider()
        self.news_spider = EntertainmentNewsSpider()

        # 深度微博爬虫（按需初始化）
        self.deep_spider = None
        if weibo_mode == "deep" and weibo_cookie:
            self.deep_spider = WeiboDeepSpider(weibo_cookie)

        # 加载 UID 映射
        self.uid_map = self._load_uid_map()

        self.results = []
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
        }

    def _load_uid_map(self) -> dict:
        """加载微博 UID 映射"""
        map_path = Path(__file__).parent / "weibo_uid_map.json"
        if map_path.exists():
            with open(map_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    async def scrape_celebrity(self, name: str) -> ScrapeResult:
        """爬取单个明星 - 使用所有数据源"""
        print(f"\n{'='*60}")
        if self.mock_mode:
            print(f"🎭 模拟模式: {name}")
        else:
            print(f"🎯 开始爬取: {name}")
        print(f"{'='*60}")

        # 模拟模式
        if self.mock_mode:
            print(f"📋 使用模拟数据...")
            result = generate_mock_result(name)
            result.data_completeness = self._calculate_completeness(result)

            print(f"\n{'='*60}")
            print(f"✅ 模拟完成! 共获取:")
            print(f"  📱 社交媒体: {len(result.social_media_posts)} 条")
            print(f"  💬 评论: {len(result.comments)} 条")
            print(f"  📰 新闻: {len(result.news_articles)} 条")
            print(f"  👥 关系: {len(result.relationships)} 条")
            print(f"  🎭 八卦: {len(result.gossips)} 条")
            print(f"  📊 数据完整度: {result.data_completeness:.1%}")
            print(f"{'='*60}\n")

            return result

        # 真实爬取模式

        # 1. 百度百科基础信息
        print(f"[1/6] 📚 爬取百度百科...")
        basic_result = await self.baike_spider.scrape_celebrity(name)
        self.stats["total_requests"] += 1
        if basic_result.celebrity.biography:
            self.stats["successful_requests"] += 1

        # 初始化结果
        result = ScrapeResult(
            celebrity=basic_result.celebrity,
            gossips=basic_result.gossips,
            relationships=basic_result.relationships
        )

        if not self.enable_all_sources:
            print(f"  ⚠️  其他数据源已禁用，仅使用百度百科")
            return result

        # 2. 微博动态
        print(f"[2/6] 📱 搜索微博动态...")
        try:
            if self.weibo_mode == "deep" and self.deep_spider:
                # 深度爬取模式
                uid = self.uid_map.get(name, "")
                if uid:
                    data = self.deep_spider.scrape_celebrity(name, uid, post_pages=5)
                    if data:
                        # 更新 celebrity profile
                        wb_profile = data['profile']
                        result.celebrity.weibo_id = wb_profile.get('id', '')
                        result.celebrity.weibo_followers = wb_profile.get('followers', 0)
                        if wb_profile.get('description'):
                            result.celebrity.biography = wb_profile['description']
                        if wb_profile.get('birthday'):
                            result.celebrity.birth_date = wb_profile['birthday']
                        result.celebrity.updated_at = datetime.now()

                        # 转换微博动态
                        posts = convert_to_social_posts(data['posts'], name)
                        result.social_media_posts.extend(posts)
                        print(f"  ✓ 深度爬取完成: {len(posts)} 条微博, "
                              f"粉丝 {wb_profile.get('followers', 0):,}")
                    else:
                        print(f"  ✗ 深度爬取失败，尝试 API 模式...")
                        await self._scrape_weibo_api(name, result)
                else:
                    print(f"  ⚠ UID 映射中未找到 {name}，尝试 API 模式...")
                    await self._scrape_weibo_api(name, result)
            else:
                # API 模式
                await self._scrape_weibo_api(name, result)

        except Exception as e:
            print(f"  ✗ 微博爬取失败: {e}")
            self.stats["failed_requests"] += 1

        # 3. 知乎讨论
        print(f"[3/6] 💡 搜索知乎讨论...")
        try:
            zhihu_data = await self.zhihu_spider.search_celebrity_topic(name)
            questions = zhihu_data.get('questions', [])
            print(f"  ✓ 找到 {len(questions)} 个相关问题")

            # 获取热门回答
            for i, q in enumerate(questions[:3], 1):
                answers = await self.zhihu_spider.scrape_answers(str(q['id']), count=5)
                result.social_media_posts.extend(answers)
                print(f"    - Q{i}: {q.get('title', '')[:30]}... ({len(answers)} 回答)")

                # 获取评论
                if answers:
                    comments = await self.zhihu_spider.scrape_comments(answers[0].id, count=15)
                    result.comments.extend(comments)

                await asyncio.sleep(1)

        except Exception as e:
            print(f"  ✗ 知乎爬取失败: {e}")
            self.stats["failed_requests"] += 1

        # 4. 豆瓣讨论
        print(f"[4/6] 🎬 搜索豆瓣讨论...")
        try:
            douban_topics = await self.douban_spider.search_gossip_groups(name)
            result.social_media_posts.extend(douban_topics)
            print(f"  ✓ 获取 {len(douban_topics)} 条豆瓣讨论")

            # 获取评论
            for topic in douban_topics[:2]:
                if topic.source_url:
                    comments = await self.douban_spider.scrape_topic_comments(topic.source_url, count=10)
                    result.comments.extend(comments)
                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  ✗ 豆瓣爬取失败: {e}")
            self.stats["failed_requests"] += 1

        # 5. 娱乐新闻
        print(f"[5/6] 📰 搜索娱乐新闻...")
        try:
            news_articles = await self.news_spider.search_gossip_keywords(name)
            result.news_articles.extend(news_articles)
            print(f"  ✓ 获取 {len(news_articles)} 条娱乐新闻")

            # 统计情感分布
            sentiments = {}
            for news in news_articles:
                sentiments[news.sentiment] = sentiments.get(news.sentiment, 0) + 1
            if sentiments:
                print(f"    情感分布: {sentiments}")

        except Exception as e:
            print(f"  ✗ 新闻爬取失败: {e}")
            self.stats["failed_requests"] += 1

        # 6. 微博热搜
        print(f"[6/6] 🔥 检查热搜...")
        try:
            hot_search = await self.weibo_spider.get_hot_search()
            related_hot = [h for h in hot_search if name in h.get('title', '')]
            if related_hot:
                print(f"  ✓ 发现 {len(related_hot)} 条相关热搜:")
                for hot in related_hot[:3]:
                    print(f"    - {hot.get('rank', '')}. {hot.get('title', '')}")
                result.celebrity.hot_search_count = len(related_hot)
        except Exception as e:
            print(f"  ✗ 热搜检查失败: {e}")

        # 计算数据完整度
        result.data_completeness = self._calculate_completeness(result)

        # 输出汇总
        print(f"\n{'='*60}")
        print(f"✅ 完成! 共获取:")
        print(f"  📱 社交媒体: {len(result.social_media_posts)} 条")
        print(f"  💬 评论: {len(result.comments)} 条")
        print(f"  📰 新闻: {len(result.news_articles)} 条")
        print(f"  👥 关系: {len(result.relationships)} 条")
        print(f"  🎭 八卦: {len(result.gossips)} 条")
        print(f"  📊 数据完整度: {result.data_completeness:.1%}")
        print(f"{'='*60}\n")

        # 回调通知
        if self.progress_callback:
            await self.progress_callback(name, result)

        return result

    async def _scrape_weibo_api(self, name: str, result: ScrapeResult):
        """使用移动端 API 爬取微博数据（回退方案）"""
        weibo_user = await self.weibo_spider.search_celebrity(name)
        if weibo_user:
            print(f"  ✓ 找到微博用户: {weibo_user.get('name')} "
                  f"({weibo_user.get('followers_count', 0):,} 粉丝)")

            posts = await self.weibo_spider.scrape_posts(weibo_user['uid'], count=15)
            result.social_media_posts.extend(posts)
            print(f"  ✓ 获取 {len(posts)} 条微博")

            result.celebrity.weibo_id = weibo_user['uid']
            result.celebrity.weibo_followers = weibo_user.get('followers_count', 0)
            result.celebrity.avatar_url = weibo_user.get('avatar', '')

            if posts:
                comments = await self.weibo_spider.scrape_comments(posts[0].id, count=30)
                result.comments.extend(comments)
                print(f"  ✓ 获取 {len(comments)} 条评论")
        else:
            print(f"  ✗ 未找到微博用户")

        # 搜索八卦相关微博
        gossip_keywords = [f"{name} 八卦", f"{name} 绯闻", f"{name} 热搜"]
        for keyword in gossip_keywords:
            gossip_posts = await self.weibo_spider.search_gossip(keyword, count=5)
            result.social_media_posts.extend(gossip_posts)
            if gossip_posts:
                print(f"  ✓ 搜索'{keyword}'到 {len(gossip_posts)} 条微博")
            await asyncio.sleep(1)

    def _calculate_completeness(self, result: ScrapeResult) -> float:
        """计算数据完整度"""
        score = 0.0
        max_score = 10.0

        # 基本信息完整度
        if result.celebrity.name:
            score += 1
        if result.celebrity.biography:
            score += 1
        if result.celebrity.occupation:
            score += 1
        if result.celebrity.birth_date:
            score += 1
        if result.celebrity.avatar_url:
            score += 0.5

        # 数据丰富度
        if len(result.social_media_posts) > 10:
            score += 1.5
        elif len(result.social_media_posts) > 0:
            score += 0.5

        if len(result.news_articles) > 5:
            score += 1.5
        elif len(result.news_articles) > 0:
            score += 0.5

        if len(result.comments) > 20:
            score += 1.5
        elif len(result.comments) > 0:
            score += 0.5

        if len(result.relationships) > 0:
            score += 1

        return min(score / max_score, 1.0)

    async def scrape_batch(
        self,
        names: list[str],
        save_after_each: bool = True,
        continue_on_error: bool = True
    ) -> list[ScrapeResult]:
        """批量爬取明星"""
        results = []

        for i, name in enumerate(names, 1):
            print(f"\n{'#'*60}")
            print(f"📋 进度: [{i}/{len(names)}] 处理: {name}")
            print(f"{'#'*60}")

            try:
                result = await self.scrape_celebrity(name)
                results.append(result)

                # 每次爬取后保存
                if save_after_each:
                    self._save_result(result)

                # 间隔延迟
                if i < len(names):
                    delay = 3
                    print(f"⏳ 等待 {delay} 秒后继续...")
                    await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ 爬取失败 {name}: {e}")
                if not continue_on_error:
                    raise

        self.results = results

        # 保存汇总
        if save_after_each:
            self.save_summary()

        return results

    def _save_result(self, result: ScrapeResult):
        """保存爬取结果"""
        name = result.celebrity.name
        safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")

        # 保存JSON
        json_path = self.output_dir / f"{safe_name}.json"
        data = {
            "celebrity": {
                "name": result.celebrity.name,
                "english_name": result.celebrity.english_name,
                "birth_date": result.celebrity.birth_date,
                "birth_place": result.celebrity.birth_place,
                "age": result.celebrity.age,
                "zodiac": result.celebrity.zodiac,
                "constellation": result.celebrity.constellation,
                "occupation": result.celebrity.occupation,
                "company": result.celebrity.company,
                "agency": result.celebrity.agency,
                "height": result.celebrity.height,
                "weight": result.celebrity.weight,
                "blood_type": result.celebrity.blood_type,
                "biography": result.celebrity.biography[:500] if result.celebrity.biography else "",
                "education": result.celebrity.education,
                "alma_mater": result.celebrity.alma_mater,
                "works": result.celebrity.works[:20],
                "famous_works": result.celebrity.famous_works[:20],
                "weibo_id": result.celebrity.weibo_id,
                "weibo_followers": result.celebrity.weibo_followers,
                "avatar_url": result.celebrity.avatar_url,
                "popularity_score": result.celebrity.popularity_score,
                "hot_search_count": result.celebrity.hot_search_count,
                "sources": result.celebrity.sources[:10],
                "updated_at": result.celebrity.updated_at.isoformat()
            },
            "gossips": [
                {
                    "title": g.title,
                    "content": g.content[:300],
                    "gossip_type": g.gossip_type.value if isinstance(g.gossip_type, GossipType) else str(g.gossip_type),
                    "date": g.date,
                    "involved_celebrities": g.involved_celebrities,
                    "tags": g.tags,
                    "importance": g.importance,
                    "verified": g.verified,
                    "sentiment": g.sentiment,
                    "sentiment_score": g.sentiment_score,
                    "source_url": g.source_url,
                    "source_type": g.source_type.value if isinstance(g.source_type, DataSourceType) else str(g.source_type)
                }
                for g in result.gossips[:20]
            ],
            "relationships": [
                {
                    "person_a": r.person_a,
                    "person_b": r.person_b,
                    "relation_type": r.relation_type,
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "is_current": r.is_current,
                    "description": r.description,
                    "confidence": r.confidence,
                    "strength": r.strength
                }
                for r in result.relationships[:30]
            ],
            "social_media_posts": [
                {
                    "id": p.id,
                    "platform": p.platform,
                    "author": p.author,
                    "content": p.content[:300],
                    "likes": p.likes,
                    "reposts": p.reposts,
                    "comments": p.comments,
                    "publish_time": p.publish_time,
                    "source_url": p.source_url,
                    "tags": p.tags[:5],
                    "topics": p.topics[:5]
                }
                for p in result.social_media_posts[:50]
            ],
            "comments": [
                {
                    "content": c.content[:200],
                    "author": c.author,
                    "likes": c.likes,
                    "replies": c.replies,
                    "is_top": c.is_top,
                    "source_platform": c.source_platform,
                    "sentiment": c.sentiment
                }
                for c in result.comments[:100]
            ],
            "news_articles": [
                {
                    "title": n.title,
                    "summary": n.summary[:200],
                    "content": n.content[:300],
                    "publish_date": n.publish_date,
                    "source": n.source,
                    "source_url": n.source_url,
                    "sentiment": n.sentiment,
                    "sentiment_score": n.sentiment_score,
                    "category": n.category,
                    "tags": n.tags[:5]
                }
                for n in result.news_articles[:30]
            ],
            "statistics": {
                "data_completeness": result.data_completeness,
                "total_posts": len(result.social_media_posts),
                "total_comments": len(result.comments),
                "total_news": len(result.news_articles),
                "total_relationships": len(result.relationships),
                "total_gossips": len(result.gossips)
            }
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  💾 保存: {json_path}")

    def save_summary(self):
        """保存爬取摘要"""
        summary = {
            "scraped_at": datetime.now().isoformat(),
            "total_celebrities": len(self.results),
            "stats": self.stats,
            "totals": {
                "social_media_posts": sum(len(r.social_media_posts) for r in self.results),
                "comments": sum(len(r.comments) for r in self.results),
                "news_articles": sum(len(r.news_articles) for r in self.results),
                "relationships": sum(len(r.relationships) for r in self.results),
                "gossips": sum(len(r.gossips) for r in self.results),
            },
            "celebrities": [
                {
                    "name": r.celebrity.name,
                    "occupation": r.celebrity.occupation,
                    "works_count": len(r.celebrity.works),
                    "relationships_count": len(r.relationships),
                    "social_media_posts_count": len(r.social_media_posts),
                    "comments_count": len(r.comments),
                    "news_articles_count": len(r.news_articles),
                    "gossips_count": len(r.gossips),
                    "has_biography": bool(r.celebrity.biography),
                    "weibo_followers": r.celebrity.weibo_followers,
                    "data_completeness": r.data_completeness
                }
                for r in self.results
            ]
        }

        summary_path = self.output_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n📊 摘要保存: {summary_path}")

    async def close(self):
        """关闭所有爬虫"""
        await self.baike_spider.close()
        await self.weibo_spider.close()
        await self.zhihu_spider.close()
        await self.douban_spider.close()
        await self.news_spider.close()


async def main():
    """主函数"""
    import os
    os.chdir("/Users/chenwei/CC/pr")

    scraper = CelebrityScraper(output_dir="celebrity_scraper/data")

    print("=" * 60)
    print("🌟 明星信息爬虫 🌟")
    print("=" * 60)

    # 爬取10位明星
    results = await scraper.scrape_batch(
        names=TOP_CELEBRITIES,
        save_after_each=True
    )

    await scraper.close()

    print("\n" + "=" * 60)
    print(f"🎉 全部完成! 共爬取 {len(results)} 位明星")
    print(f"📊 成功率: {scraper.stats['successful_requests']}/{scraper.stats['total_requests']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
