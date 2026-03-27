"""
明星爬虫主程序 - 协调多个爬虫
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from datetime import datetime

from .spiders import BaiduBaikeSpider
from .models import CelebrityProfile, ScrapeResult


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


class CelebrityScraper:
    """明星爬虫主类"""

    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.spider = BaiduBaikeSpider()
        self.results = []

    async def scrape_celebrity(self, name: str) -> ScrapeResult:
        """爬取单个明星"""
        return await self.spider.scrape_celebrity(name)

    async def scrape_batch(
        self,
        names: list[str],
        save_after_each: bool = True
    ) -> list[ScrapeResult]:
        """批量爬取明星"""
        results = []

        for i, name in enumerate(names, 1):
            print(f"\n[{i}/{len(names)}] 正在处理: {name}")

            try:
                result = await self.scrape_celebrity(name)
                results.append(result)

                # 每次爬取后保存
                if save_after_each:
                    self._save_result(result)

                # 间隔延迟
                if i < len(names):
                    await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ 爬取失败 {name}: {e}")

        self.results = results
        return results

    def _save_result(self, result: ScrapeResult):
        """保存爬取结果"""
        name = result.celebrity.name
        safe_name = name.replace("/", "_").replace("\\", "_")

        # 保存JSON
        json_path = self.output_dir / f"{safe_name}.json"
        data = {
            "celebrity": {
                "name": result.celebrity.name,
                "english_name": result.celebrity.english_name,
                "birth_date": result.celebrity.birth_date,
                "birth_place": result.celebrity.birth_place,
                "occupation": result.celebrity.occupation,
                "company": result.celebrity.company,
                "height": result.celebrity.height,
                "zodiac": result.celebrity.zodiac,
                "biography": result.celebrity.biography,
                "education": result.celebrity.education,
                "works": result.celebrity.works,
                "sources": result.celebrity.sources,
                "updated_at": result.celebrity.updated_at.isoformat()
            },
            "gossips": [
                {
                    "title": g.title,
                    "content": g.content,
                    "date": g.date,
                    "involved_celebrities": g.involved_celebrities,
                    "tags": g.tags,
                    "importance": g.importance
                }
                for g in result.gossips
            ],
            "relationships": [
                {
                    "person_a": r.person_a,
                    "person_b": r.person_b,
                    "relation_type": r.relation_type,
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "description": r.description,
                    "confidence": r.confidence
                }
                for r in result.relationships
            ]
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  保存: {json_path}")

    def save_summary(self):
        """保存爬取摘要"""
        summary = {
            "scraped_at": datetime.now().isoformat(),
            "total_celebrities": len(self.results),
            "celebrities": [
                {
                    "name": r.celebrity.name,
                    "occupation": r.celebrity.occupation,
                    "works_count": len(r.celebrity.works),
                    "relationships_count": len(r.relationships),
                    "has_biography": bool(r.celebrity.biography)
                }
                for r in self.results
            ]
        }

        summary_path = self.output_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n摘要保存: {summary_path}")

    async def close(self):
        """关闭爬虫"""
        await self.spider.close()


async def main():
    """主函数"""
    import os
    os.chdir("/Users/chenwei/CC/pr")

    scraper = CelebrityScraper(output_dir="celebrity_scraper/data")

    print("=" * 50)
    print("明星信息爬虫")
    print("=" * 50)

    # 爬取10位明星
    results = await scraper.scrape_batch(
        names=TOP_CELEBRITIES,
        save_after_each=True
    )

    # 保存摘要
    scraper.save_summary()

    await scraper.close()

    print("\n" + "=" * 50)
    print(f"完成! 共爬取 {len(results)} 位明星")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
