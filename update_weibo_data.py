#!/usr/bin/env python3
"""
微博数据更新脚本 - 使用 weiboSpider 爬取真实微博数据并更新明星资料

使用方法:
  # 验证 cookie
  python update_weibo_data.py --cookie "YOUR_COOKIE" --validate

  # 更新指定明星
  python update_weibo_data.py --cookie "YOUR_COOKIE" --names 杨幂 赵丽颖

  # 从文件读取 cookie 并更新所有明星
  python update_weibo_data.py --cookie-file weibo_cookie.txt --all

  # 使用环境变量 WEIBO_COOKIE
  export WEIBO_COOKIE="your_cookie"
  python update_weibo_data.py --all
"""

import argparse
import json
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from celebrity_scraper.spiders.weibo_deep_spider import (
    WeiboDeepSpider,
    convert_to_social_posts,
)
from celebrity_scraper.mock_data import (
    generate_mock_gossips,
    generate_mock_relationships,
    generate_mock_news,
)
from celebrity_scraper.models import GossipType, DataSourceType


# 默认明星列表
TOP_CELEBRITIES = [
    "肖战", "王一博", "杨幂", "赵丽颖", "迪丽热巴",
    "唐嫣", "罗晋", "李小璐", "贾乃亮", "PG One",
]


def load_uid_map() -> dict:
    """加载 UID 映射"""
    map_path = Path(__file__).parent / "celebrity_scraper" / "weibo_uid_map.json"
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_uid_map(uid_map: dict):
    """保存 UID 映射"""
    map_path = Path(__file__).parent / "celebrity_scraper" / "weibo_uid_map.json"
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(uid_map, f, ensure_ascii=False, indent=2)


def get_cookie(args) -> str:
    """获取 cookie"""
    if args.cookie:
        return args.cookie
    if args.cookie_file:
        cookie_path = Path(args.cookie_file)
        if not cookie_path.exists():
            print(f"❌ Cookie 文件不存在: {cookie_path}")
            sys.exit(1)
        return cookie_path.read_text(encoding='utf-8').strip()
    # 从环境变量读取
    cookie = os.environ.get('WEIBO_COOKIE', '')
    if not cookie:
        print("❌ 未提供 Cookie。请通过以下方式之一提供:")
        print("  --cookie 'YOUR_COOKIE'")
        print("  --cookie-file cookie.txt")
        print("  环境变量 WEIBO_COOKIE")
        sys.exit(1)
    return cookie


def update_celebrity(spider: WeiboDeepSpider, name: str, uid: str,
                     output_dir: Path, uid_map: dict) -> bool:
    """爬取并更新单个明星数据"""
    print(f"\n{'='*60}")
    print(f"📋 爬取: {name} (UID: {uid})")
    print(f"{'='*60}")

    # 爬取微博数据
    data = spider.scrape_celebrity(name, uid, post_pages=5)
    if not data:
        print(f"  ❌ 爬取失败: {name}")
        return False

    profile = data['profile']
    posts = data['posts']

    # 更新 UID 映射（如果有变化）
    if uid != profile.get('id', uid):
        uid_map[name] = profile['id']

    # 转换微博数据
    social_posts = convert_to_social_posts(posts, name)

    # 生成 mock 数据补充（gossips/relationships/news）
    mock_gossips = generate_mock_gossips(name)
    mock_rels = generate_mock_relationships(name)
    mock_news = generate_mock_news(name, count=5)

    # 构建完整 JSON
    celebrity_data = {
        "celebrity": {
            "name": name,
            "english_name": "",
            "birth_date": profile.get('birthday', '') or None,
            "birth_place": profile.get('location', ''),
            "age": 0,
            "zodiac": "",
            "constellation": "",
            "occupation": [],
            "company": "",
            "agency": "",
            "height": "",
            "weight": "",
            "blood_type": "",
            "biography": profile.get('description', ''),
            "education": profile.get('education', ''),
            "alma_mater": "",
            "works": [],
            "famous_works": [],
            "weibo_id": profile.get('id', ''),
            "weibo_followers": profile.get('followers', 0),
            "avatar_url": "",
            "popularity_score": 0.0,
            "hot_search_count": 0,
            "sources": ["weibo"],
            "updated_at": datetime.now().isoformat(),
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
                "source_type": g.source_type.value if isinstance(g.source_type, DataSourceType) else str(g.source_type),
            }
            for g in mock_gossips
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
                "strength": r.strength,
            }
            for r in mock_rels
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
                "topics": p.topics[:5],
            }
            for p in social_posts
        ],
        "comments": [],
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
                "tags": n.tags[:5],
            }
            for n in mock_news
        ],
        "statistics": {
            "data_completeness": 0.0,
            "total_posts": len(social_posts),
            "total_comments": 0,
            "total_news": len(mock_news),
            "total_relationships": len(mock_rels),
            "total_gossips": len(mock_gossips),
        },
    }

    # 计算数据完整度
    score = 0.0
    if celebrity_data["celebrity"]["name"]:
        score += 1
    if celebrity_data["celebrity"]["biography"]:
        score += 1
    if celebrity_data["celebrity"]["weibo_followers"] > 0:
        score += 1
    if celebrity_data["celebrity"]["birth_date"]:
        score += 1
    if len(social_posts) > 10:
        score += 1.5
    elif len(social_posts) > 0:
        score += 0.5
    if len(mock_news) > 0:
        score += 0.5
    if len(mock_rels) > 0:
        score += 1
    celebrity_data["statistics"]["data_completeness"] = min(score / 10.0, 1.0)

    # 保存 JSON
    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    json_path = output_dir / f"{safe_name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(celebrity_data, f, ensure_ascii=False, indent=2)

    print(f"  💾 已保存: {json_path}")
    print(f"  📊 微博 {len(social_posts)} 条 | 关系 {len(mock_rels)} 条 | "
          f"八卦 {len(mock_gossips)} 条 | 新闻 {len(mock_news)} 条")
    return True


def main():
    parser = argparse.ArgumentParser(description='微博数据更新工具')
    parser.add_argument('--cookie', type=str, help='微博 Cookie 字符串')
    parser.add_argument('--cookie-file', type=str, help='Cookie 文件路径')
    parser.add_argument('--names', nargs='+', help='指定明星名称')
    parser.add_argument('--all', action='store_true', help='更新所有 TOP_CELEBRITIES')
    parser.add_argument('--validate', action='store_true', help='仅验证 Cookie 是否有效')
    parser.add_argument('--output-dir', type=str,
                        default='celebrity_scraper/data',
                        help='输出目录 (默认: celebrity_scraper/data)')
    parser.add_argument('--pages', type=int, default=5,
                        help='每个明星爬取的微博页数 (默认: 5)')

    args = parser.parse_args()

    # 获取 cookie
    cookie = get_cookie(args)

    # 初始化爬虫
    spider = WeiboDeepSpider(cookie)

    # 验证 cookie
    print("🔍 验证 Cookie...")
    if not spider.validate_cookie():
        print("❌ Cookie 无效或已过期!")
        print("\n获取 Cookie 步骤:")
        print("  1. 浏览器打开 https://weibo.cn")
        print("  2. 登录微博账号")
        print("  3. F12 → Network → 刷新页面")
        print("  4. 点击第一个请求 → Headers → Request Headers")
        print("  5. 复制完整的 Cookie 值")
        sys.exit(1)
    print("✅ Cookie 有效!")

    if args.validate:
        return

    # 加载 UID 映射
    uid_map = load_uid_map()

    # 确定要爬取的明星
    if args.all:
        names = TOP_CELEBRITIES
    elif args.names:
        names = args.names
    else:
        print("❌ 请指定 --names 或 --all")
        parser.print_help()
        sys.exit(1)

    # 输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # 逐个爬取
    success_count = 0
    fail_count = 0
    skipped = []

    for i, name in enumerate(names, 1):
        uid = uid_map.get(name, "")
        if not uid:
            print(f"\n⚠️  [{i}/{len(names)}] 跳过 {name}: 无 UID 映射")
            skipped.append(name)
            continue

        print(f"\n[{i}/{len(names)}] ", end="")
        try:
            if update_celebrity(spider, name, uid, output_dir, uid_map):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            fail_count += 1

        # 间隔延迟
        if i < len(names) and uid:
            delay = random.uniform(5, 10)
            print(f"  ⏳ 等待 {delay:.1f} 秒...")
            time.sleep(delay)

    # 保存更新后的 UID 映射
    save_uid_map(uid_map)

    # 生成 summary
    summary = {
        "scraped_at": datetime.now().isoformat(),
        "mode": "weibo_deep",
        "total_celebrities": success_count,
        "results": {
            "success": success_count,
            "failed": fail_count,
            "skipped": skipped,
        },
    }
    summary_path = output_dir / "summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 汇总
    print(f"\n{'='*60}")
    print(f"🎉 完成! 成功: {success_count} | 失败: {fail_count} | 跳过: {len(skipped)}")
    if skipped:
        print(f"⚠️  跳过的明星（无 UID）: {', '.join(skipped)}")
    print(f"📊 摘要: {summary_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
