"""
测试爬虫 - 单个明星测试
"""

import asyncio
import sys
import os

# 确保在正确的目录
os.chdir("/Users/chenwei/CC/pr")

from celebrity_scraper.scraper import CelebrityScraper, TOP_CELEBRITIES, GOSSIP_CELEBRITIES
from celebrity_scraper.mock_data import get_available_celebrities


async def test_single_celebrity(name: str = "杨幂", mock_mode: bool = False):
    """测试单个明星爬取"""
    mode_str = "模拟模式" if mock_mode else "真实爬取"
    print(f"\n{'='*60}")
    print(f"🧪 {mode_str}: {name}")
    print(f"{'='*60}\n")

    scraper = CelebrityScraper(
        output_dir="celebrity_scraper/data",
        enable_all_sources=True,
        mock_mode=mock_mode
    )

    # 爬取一个明星
    result = await scraper.scrape_celebrity(name)

    # 输出结果摘要
    print(f"\n{'='*60}")
    print(f"📊 结果摘要:")
    print(f"{'='*60}")
    print(f"姓名: {result.celebrity.name}")
    print(f"英文名: {result.celebrity.english_name}")
    print(f"职业: {', '.join(result.celebrity.occupation)}")
    print(f"生日: {result.celebrity.birth_date}")
    print(f"出生地: {result.celebrity.birth_place}")
    print(f"星座: {result.celebrity.constellation}")
    print(f"经纪公司: {result.celebrity.company}")
    print(f"简介: {result.celebrity.biography[:150] if result.celebrity.biography else '无'}...")
    print(f"\n代表作: {', '.join(result.celebrity.famous_works) if result.celebrity.famous_works else '无'}")
    print(f"\n📊 数据统计:")
    print(f"  社交媒体: {len(result.social_media_posts)} 条")
    print(f"  评论: {len(result.comments)} 条")
    print(f"  新闻: {len(result.news_articles)} 条")
    print(f"  关系: {len(result.relationships)} 条")
    print(f"  八卦: {len(result.gossips)} 条")
    print(f"  数据完整度: {result.data_completeness:.1%}")

    # 显示八卦
    if result.gossips:
        print(f"\n🎭 八卦事件:")
        for gossip in result.gossips[:5]:
            print(f"  - {gossip.title} ({gossip.gossip_type.value})")

    # 显示关系
    if result.relationships:
        print(f"\n👥 人际关系:")
        for rel in result.relationships[:5]:
            print(f"  - {rel.person_a} -{rel.relation_type}-> {rel.person_b}")

    # 保存结果
    scraper._save_result(result)

    await scraper.close()

    print(f"\n✅ 测试完成!")

    return result


async def test_batch(names: list[str], mock_mode: bool = False):
    """批量测试"""
    mode_str = "模拟模式" if mock_mode else "真实爬取"
    print(f"\n{'='*60}")
    print(f"🧪 批量测试 - {mode_str}")
    print(f"{'='*60}")

    scraper = CelebrityScraper(
        output_dir="celebrity_scraper/data",
        enable_all_sources=True,
        mock_mode=mock_mode
    )

    results = await scraper.scrape_batch(
        names=names,
        save_after_each=True
    )

    await scraper.close()

    print(f"\n✅ 批量测试完成! 共处理 {len(results)} 位明星")

    return results


async def test_quick():
    """快速测试 - 模拟模式"""
    print(f"\n{'='*60}")
    print(f"🧪 快速测试 - 模拟数据")
    print(f"{'='*60}\n")

    # 显示可用的明星
    available = get_available_celebrities()
    print(f"📋 可用明星: {', '.join(available[:10])}")

    scraper = CelebrityScraper(
        output_dir="celebrity_scraper/data",
        enable_all_sources=False,
        mock_mode=True
    )

    result = await scraper.scrape_celebrity("肖战")

    print(f"\n姓名: {result.celebrity.name}")
    print(f"职业: {', '.join(result.celebrity.occupation)}")
    print(f"代表作: {', '.join(result.celebrity.famous_works)}")
    print(f"八卦: {len(result.gossips)} 条")

    await scraper.close()

    return result


def print_usage():
    """打印使用说明"""
    print("""
用法: python test_scraper.py [选项] [参数]

选项:
  无参数       - 快速测试（模拟模式）
  mock <名字>  - 模拟模式测试指定明星
  real <名字>  - 真实爬取指定明星
  batch        - 批量测试（模拟模式，10位明星）
  list         - 显示可用的明星列表

示例:
  python test_scraper.py           # 快速测试
  python test_scraper.py mock 杨幂  # 模拟模式测试杨幂
  python test_scraper.py real 杨幂  # 真实爬取杨幂
  python test_scraper.py batch     # 批量测试
  python test_scraper.py list      # 显示可用明星
    """)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        asyncio.run(test_quick())
    elif sys.argv[1] == "mock" and len(sys.argv) > 2:
        name = " ".join(sys.argv[2:])
        asyncio.run(test_single_celebrity(name, mock_mode=True))
    elif sys.argv[1] == "real" and len(sys.argv) > 2:
        name = " ".join(sys.argv[2:])
        asyncio.run(test_single_celebrity(name, mock_mode=False))
    elif sys.argv[1] == "batch":
        asyncio.run(test_batch(TOP_CELEBRITIES[:5], mock_mode=True))
    elif sys.argv[1] == "list":
        available = get_available_celebrities()
        print(f"\n可用明星列表 ({len(available)} 位):")
        for i, name in enumerate(available, 1):
            print(f"  {i:2}. {name}")
    elif sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
    else:
        print_usage()
        asyncio.run(test_quick())
