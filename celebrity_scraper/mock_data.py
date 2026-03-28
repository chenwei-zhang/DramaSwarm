# -*- coding: utf-8 -*-
"""
模拟数据生成器 - 用于测试和演示

数据更新至 2024-2026 年，反映明星最新动态。
"""

from __future__ import annotations

from datetime import datetime, timedelta
import random
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from celebrity_scraper.models import (
    CelebrityProfile, GossipItem, Relationship, ScrapeResult,
    NewsArticle, Comment, SocialMediaPost, GossipType, DataSourceType
)


# 明星基础数据 - 2024-2026 更新版
CELEBRITY_DATA = {
    "肖战": {
        "english_name": "Xiao Zhan",
        "birth_date": "1991-10-05",
        "birth_place": "重庆市",
        "constellation": "天秤座",
        "occupation": ["演员", "歌手"],
        "company": "肖战工作室",
        "biography": "肖战，中国内地影视男演员、歌手。2015年以X玖少年团成员身份出道，2019年因出演《陈情令》魏无羡一角爆红。近年与徐克、郑晓龙、孔笙等顶级导演合作，成功转型实力派路线。2025年春节档主演徐克执导的《射雕英雄传：侠之大者》。",
        "famous_works": ["陈情令", "斗罗大陆", "王牌部队", "梦中的那片海", "骄阳伴我", "射雕英雄传：侠之大者", "藏海传"],
        "weibo_followers": 32000000,
        "avatar_url": "https://example.com/xiaozhan.jpg",
        "height": "183cm",
        "zodiac": "羊"
    },
    "王一博": {
        "english_name": "Wang Yibo",
        "birth_date": "1997-08-05",
        "birth_place": "河南省洛阳市",
        "constellation": "狮子座",
        "occupation": ["演员", "歌手", "摩托车赛车手", "舞者"],
        "company": "乐华娱乐",
        "biography": "王一博，中国内地男演员、歌手、职业摩托车赛车手。2014年以UNIQ组合出道，2019年凭《陈情令》蓝忘机走红。近年深耕电影领域，主演《无名》《长空之王》《热烈》等影片。同时也是Discovery户外探索节目《探索新境》主角。",
        "famous_works": ["陈情令", "有翡", "风起洛阳", "无名", "长空之王", "热烈", "探索新境"],
        "weibo_followers": 41000000,
        "height": "180cm",
        "zodiac": "牛"
    },
    "杨幂": {
        "english_name": "Yang Mi",
        "birth_date": "1986-09-12",
        "birth_place": "北京市",
        "constellation": "处女座",
        "occupation": ["演员", "歌手", "制片人"],
        "company": "杨幂工作室",
        "biography": "杨幂，中国内地影视女演员、流行乐歌手、制片人。2006年因《神雕侠侣》崭露头角，2011年凭《宫》爆红。2023年离开嘉行传媒成立个人工作室，近年尝试转型正剧路线。2024年主演《狐妖小红娘·月红篇》《哈尔滨一九四四》等作品。微博粉丝超1.1亿，是中国最具人气的女星之一。",
        "famous_works": ["宫", "仙剑奇侠传三", "三生三世十里桃花", "狐妖小红娘·月红篇", "哈尔滨一九四四", "生万物"],
        "weibo_followers": 112000000,
        "height": "166cm",
        "zodiac": "虎"
    },
    "赵丽颖": {
        "english_name": "Zhao Liying",
        "birth_date": "1987-10-16",
        "birth_place": "河北省廊坊市",
        "constellation": "天秤座",
        "occupation": ["演员"],
        "company": "赵丽颖工作室",
        "biography": "赵丽颖，中国内地影视女演员。2015年凭《花千骨》打破收视纪录，2021年与冯绍峰离婚后专注事业转型。2024年凭张艺谋电影《第二十条》获口碑突破，主演《与凤行》再掀热潮。微博粉丝超9000万，从流量花成功转型实力派。",
        "famous_works": ["花千骨", "知否知否应是绿肥红瘦", "风吹半夏", "与凤行", "第二十条", "乔妍的心事"],
        "weibo_followers": 92000000,
        "height": "165cm",
        "zodiac": "兔"
    },
    "迪丽热巴": {
        "english_name": "Dilraba",
        "birth_date": "1992-06-03",
        "birth_place": "新疆乌鲁木齐市",
        "constellation": "双子座",
        "occupation": ["演员"],
        "company": "嘉行传媒",
        "biography": "迪丽热巴，中国内地影视女演员，维吾尔族。2015年凭《克拉恋人》崭露头角，2017年《三生三世十里桃花》凤九一角人气暴涨。作为嘉行传媒当家花旦，近年有多部待播剧储备。微博粉丝超8000万，商业价值极高。",
        "famous_works": ["克拉恋人", "三生三世十里桃花", "长歌行", "与君初相识", "安乐传", "枭起青壤"],
        "weibo_followers": 82000000,
        "height": "168cm",
        "zodiac": "猴"
    },
    "唐嫣": {
        "english_name": "Tiffany Tang",
        "birth_date": "1983-12-06",
        "birth_place": "上海市",
        "constellation": "射手座",
        "occupation": ["演员", "歌手"],
        "company": "唐嫣工作室",
        "biography": "唐嫣，中国内地影视女演员。2009年因《仙剑奇侠传三》获得关注。2023-2024年主演王家卫导演的《繁花》饰演汪小姐，被视为演艺生涯突破性角色，口碑和商业价值大幅攀升。与罗晋2018年结婚，育有一女。",
        "famous_works": ["仙剑奇侠传三", "何以笙箫默", "锦绣未央", "燕云台", "繁花"],
        "weibo_followers": 38000000,
        "height": "172cm",
        "zodiac": "猪"
    },
    "罗晋": {
        "english_name": "Luo Jin",
        "birth_date": "1981-11-30",
        "birth_place": "江西省宜春市铜鼓县",
        "constellation": "射手座",
        "occupation": ["演员"],
        "company": "罗晋工作室",
        "biography": "罗晋，中国内地男演员。2010年主演《三国》进入观众视野。2018年与唐嫣在维也纳结婚，2020年喜得千金。近年作品有《幸福到万家》《天下长河》《埃博拉前线》等，以实力派演技著称。",
        "famous_works": ["锦绣未央", "鹤唳华亭", "幸福到万家", "天下长河", "埃博拉前线"],
        "weibo_followers": 22000000,
        "height": "178cm",
        "zodiac": "鸡"
    },
    "李小璐": {
        "english_name": "Li Xiaolu",
        "birth_date": "1981-09-30",
        "birth_place": "安徽省安庆市",
        "constellation": "天秤座",
        "occupation": ["演员", "歌手"],
        "company": "个人经营",
        "biography": "李小璐，中国内地影视女演员。1998年凭《天浴》成为最年轻金马影后。2012年与贾乃亮结婚，2019年因与PG One的夜宿门事件离婚。此后退出主流影视圈，转战短视频和直播带货领域。",
        "famous_works": ["天浴", "都是天使惹的祸", "奋斗", "当婆婆遇上妈"],
        "weibo_followers": 15000000,
        "height": "163cm",
        "zodiac": "鸡"
    },
    "贾乃亮": {
        "english_name": "Jia Nailiang",
        "birth_date": "1984-04-12",
        "birth_place": "黑龙江省哈尔滨市",
        "constellation": "白羊座",
        "occupation": ["演员", "主播"],
        "company": "贾乃亮工作室",
        "biography": "贾乃亮，中国内地男演员。2012年与李小璐结婚，2019年离婚后以好爸爸形象示人。近年成功转型直播带货，成为抖音头部明星主播，多次创高销售纪录。同时活跃于综艺节目。",
        "famous_works": ["当婆婆遇上妈", "产科男医生", "偏偏喜欢你", "推手"],
        "weibo_followers": 16000000,
        "height": "181cm",
        "zodiac": "鼠"
    },
    "PG One": {
        "english_name": "PG One",
        "birth_date": "1992-05-15",
        "birth_place": "黑龙江省哈尔滨市",
        "constellation": "金牛座",
        "occupation": ["说唱歌手", "词曲创作人"],
        "company": "独立音乐人",
        "biography": "PG One，本名王昊，中国内地说唱歌手。2017年凭《中国有嘻哈》冠军走红，同年因与李小璐夜宿门事件引发巨大争议，遭到行业封杀。此后多次尝试复出未果，以地下独立音乐人身份活动。",
        "famous_works": ["中国有嘻哈", "圣诞歌", "Rocket"],
        "weibo_followers": 500000,
        "height": "178cm",
        "zodiac": "猴"
    },
}

# 八卦事件数据库 - 精选 2019-2025 年重大事件
GOSSIP_DATABASE = [
    {
        "names": ["李小璐", "贾乃亮", "PG One"],
        "type": GossipType.CHEATING,
        "title": "李小璐PG One夜宿门事件",
        "content": "2017年底李小璐被拍到与PG One深夜亲密互动。贾乃亮当时直播中表示「相信我老婆」，但两人最终于2019年离婚。事件导致PG One遭行业封杀，李小璐退出主流影视圈。贾乃亮转型直播带货成功。该事件至今仍是娱乐圈最具影响力的丑闻之一。",
        "summary": "李小璐与PG One夜宿门事件，导致贾乃亮和李小璐离婚，PG One被封杀。",
        "date": "2017-12-29",
        "importance": 0.95,
        "verified": True
    },
    {
        "names": ["杨幂"],
        "type": GossipType.DIVORCE,
        "title": "杨幂刘恺威离婚",
        "content": "2018年12月杨幂与刘恺威官宣离婚，结束四年婚姻。女儿小糯米由双方共同抚养。两人2014年结婚，离婚原因未公开详细说明。离婚后杨幂专注事业，2023年离开嘉行传媒成立个人工作室。",
        "summary": "2018年杨幂与刘恺威官宣离婚，此后杨幂专注事业独立发展。",
        "date": "2018-12-22",
        "importance": 0.9,
        "verified": True
    },
    {
        "names": ["赵丽颖"],
        "type": GossipType.DIVORCE,
        "title": "赵丽颖冯绍峰离婚",
        "content": "2021年4月赵丽颖与冯绍峰官宣离婚，结束两年多婚姻。两人2018年结婚，婚后育有一子。离婚后赵丽颖专注事业，2024年凭电影《第二十条》和剧集《与凤行》成功转型实力派。",
        "summary": "2021年赵丽颖与冯绍峰和平离婚，此后赵丽颖事业再攀高峰。",
        "date": "2021-04-23",
        "importance": 0.9,
        "verified": True
    },
    {
        "names": ["杨幂"],
        "type": GossipType.OTHER,
        "title": "杨幂离开嘉行传媒独立发展",
        "content": "2023年5月杨幂宣布与嘉行传媒解约，结束十余年深度合作。她曾是嘉行创始股东之一，旗下艺人包括迪丽热巴等。解约后成立个人工作室独立运营，被外界视为重新掌控事业的重要一步。此后杨幂在角色选择上明显向正剧转型。",
        "summary": "2023年杨幂离开嘉行传媒成立个人工作室，向正剧转型。",
        "date": "2023-05-08",
        "importance": 0.8,
        "verified": True
    },
    {
        "names": ["唐嫣"],
        "type": GossipType.OTHER,
        "title": "唐嫣凭《繁花》事业翻红",
        "content": "2023-2024年唐嫣主演王家卫导演的《繁花》饰演汪小姐，演技获广泛好评，被视为演艺生涯突破性角色。该剧热度极高，唐嫣商业价值大幅攀升，代言增多，重回一线女星行列。",
        "summary": "唐嫣凭《繁花》汪小姐一角翻红，口碑商业双丰收。",
        "date": "2024-01-01",
        "importance": 0.85,
        "verified": True
    },
    {
        "names": ["杨幂"],
        "type": GossipType.OTHER,
        "title": "杨幂《狐妖小红娘》口碑争议",
        "content": "2024年杨幂主演的《狐妖小红娘·月红篇》在爱奇艺播出，改编自热门国漫。该剧口碑两极分化，杨幂的古装造型和演技受到不同评价，豆瓣评分不及预期。部分观众认为剧情改编过于偏离原著。",
        "summary": "杨幂《狐妖小红娘》口碑两极分化，引发演技和改编争议。",
        "date": "2024-05-23",
        "importance": 0.75,
        "verified": True
    },
    {
        "names": ["赵丽颖"],
        "type": GossipType.OTHER,
        "title": "赵丽颖《第二十条》电影口碑突破",
        "content": "2024年春节档赵丽颖出演张艺谋执导的《第二十条》，饰演听障母亲郝秀萍。表演获得观众和影评人一致好评，被视为从流量花到实力派的里程碑之作。影片票房口碑双丰收。",
        "summary": "赵丽颖凭《第二十条》演技获好评，成功转型实力派。",
        "date": "2024-02-10",
        "importance": 0.85,
        "verified": True
    },
    {
        "names": ["肖战"],
        "type": GossipType.OTHER,
        "title": "肖战《射雕英雄传》春节档上映",
        "content": "2025年春节档肖战主演的《射雕英雄传：侠之大者》上映，由徐克执导，肖战饰演郭靖。这是肖战首次挑大梁主演大制作电影，票房表现引发广泛讨论和关注。",
        "summary": "肖战2025春节档主演徐克《射雕英雄传》电影，票房话题度高。",
        "date": "2025-01-29",
        "importance": 0.8,
        "verified": True
    },
    {
        "names": ["王一博"],
        "type": GossipType.OTHER,
        "title": "王一博与乐华娱乐合约传闻",
        "content": "2024-2025年间，王一博与乐华娱乐的合约到期传闻持续发酵。作为乐华上市后商业价值最高的艺人，他的去向直接影响乐华股价。市场高度关注其是否会续约或独立发展。",
        "summary": "王一博与乐华娱乐合约到期传闻持续，去向影响公司股价。",
        "date": "2024-11-15",
        "importance": 0.7,
        "verified": False
    },
    {
        "names": ["贾乃亮"],
        "type": GossipType.OTHER,
        "title": "贾乃亮直播带货事业成功转型",
        "content": "离婚后贾乃亮成功转型直播带货，成为抖音头部明星主播。多次创造高销售纪录，涵盖美妆、食品、家电等品类。被视为明星转型直播的典型案例。同时持续活跃于综艺节目。",
        "summary": "贾乃亮转型直播带货成抖音头部主播，事业第二春。",
        "date": "2024-06-01",
        "importance": 0.65,
        "verified": True
    },
]


def generate_mock_profile(name: str) -> CelebrityProfile:
    """生成模拟明星资料"""
    data = CELEBRITY_DATA.get(name, {
        "english_name": "",
        "birth_date": "",
        "birth_place": "",
        "constellation": "",
        "occupation": ["演员"],
        "company": "",
        "biography": f"{name}，中国内地知名艺人，活跃于影视圈。",
        "famous_works": [],
        "weibo_followers": random.randint(1000000, 50000000),
        "height": "",
        "zodiac": "",
    })

    return CelebrityProfile(
        name=name,
        english_name=data.get("english_name", ""),
        birth_date=data.get("birth_date"),
        birth_place=data.get("birth_place", ""),
        constellation=data.get("constellation", ""),
        occupation=data.get("occupation", []),
        company=data.get("company", ""),
        biography=data.get("biography", ""),
        famous_works=data.get("famous_works", []),
        weibo_followers=data.get("weibo_followers", 0),
        avatar_url=data.get("avatar_url", ""),
        height=data.get("height", ""),
        zodiac=data.get("zodiac", ""),
    )


def generate_mock_posts(name: str, count: int = 20) -> list[SocialMediaPost]:
    """生成模拟社交媒体动态"""
    posts = []

    # 基于明星特点的个性化动态模板
    person_posts = {
        "杨幂": [
            "新的开始，新的角色，期待与大家分享",
            "工作日常记录，努力成为更好的自己",
            "新戏杀青了，感谢剧组每一位的付出",
            "今天阳光很好，分享一下~",
            "《哈尔滨一九四四》终于播了，忐忑又期待",
        ],
        "肖战": [
            "《藏海传》杀青，感恩遇见",
            "新的旅程开始，继续前行",
            "感谢大家一路以来的支持和陪伴",
            "今天在片场学到了很多",
            "《射雕英雄传》即将上映，紧张又期待",
        ],
        "赵丽颖": [
            "《第二十条》郝秀萍，是我演艺生涯的重要角色",
            "《与凤行》播出啦，感谢大家的喜欢",
            "每一天都在认真对待每一个角色",
            "生活中的小确幸，分享给你们",
            "感谢导演和剧组，学到了很多",
        ],
    }

    post_templates = person_posts.get(name, [
        "今天的拍摄很顺利，感谢大家的支持！",
        "新作品即将上线，敬请期待！",
        "工作花絮分享~",
        "感谢粉丝们的支持！",
        "新剧开机，加油！",
    ])

    # 通用模板补充
    generic_templates = [
        "收工啦，晚安！",
        "杂志拍摄完成，期待正片",
        "感谢品牌方的邀请",
        "剧组日常，认真工作中",
        "公益行动，传递正能量",
        "健身打卡",
        "新歌听听看",
        "路演见",
    ]

    all_templates = post_templates + generic_templates
    selected_posts = random.sample(all_templates, min(count, len(all_templates)))

    hashtags = [
        ["工作", "努力"], ["新剧", "期待"], ["日常", "分享"],
        ["感恩", "粉丝"], ["杀青", "新戏"], ["生活", "记录"],
    ]

    for i, content in enumerate(selected_posts):
        post = SocialMediaPost(
            id=f"wb_{name}_{i}",
            platform=random.choice(["weibo", "douyin", "weibo"]),
            author=name,
            author_id=f"uid_{random.randint(10000000, 99999999)}",
            author_verified=True,
            content=content,
            likes=random.randint(1000, 500000),
            reposts=random.randint(100, 50000),
            comments=random.randint(50, 10000),
            publish_time=(datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
            source_url=f"https://weibo.com/{name}/{i}",
            tags=random.choice(hashtags),
            topics=random.choice(hashtags),
        )
        posts.append(post)

    return posts


def generate_mock_comments(name: str, count: int = 50) -> list[Comment]:
    """生成模拟评论"""
    comments = []

    comment_templates = [
        "支持{}！加油",
        "{}好棒！",
        "期待新作品！",
        "{}的演技越来越好了",
        "永远支持",
        "新剧什么时候出？",
        "爱了爱了",
        "今天状态真好",
        "{}永远的神",
        "路人转粉了",
        "综艺里好搞笑",
        "这颜值真的绝了",
        "看哭了，太感人了",
    ]

    for i in range(count):
        comment = Comment(
            id=f"c_{i}",
            content=random.choice(comment_templates).format(name),
            author=f"用户{random.randint(1000, 9999)}",
            likes=random.randint(0, 5000),
            replies=random.randint(0, 100),
            is_top=random.random() < 0.1,
            source_platform=random.choice(["weibo", "douyin"]),
            sentiment=random.choice(["positive", "positive", "positive", "neutral", "negative"]),
            sentiment_score=random.uniform(-0.3, 0.9),
        )
        comments.append(comment)

    return comments


def generate_mock_news(name: str, count: int = 15) -> list[NewsArticle]:
    """生成模拟新闻 - 基于真实作品和事件"""
    news = []

    # 每个明星的个性化新闻
    person_news = {
        "杨幂": [
            ("杨幂《哈尔滨一九四四》热播，一人分饰两角挑战谍战题材", "杨幂主演的民国谍战剧《哈尔滨一九四四》正在热播，与秦昊搭档，杨幂挑战双角色演技获关注。"),
            ("杨幂独立发展后首部作品开播，转型之路引发讨论", "离开嘉行传媒后杨幂以个人工作室身份接洽项目，角色选择向正剧转型，业界关注其未来发展路径。"),
            ("杨幂《狐妖小红娘·月红篇》口碑两极，原著粉争议不断", "改编自热门国漫的《狐妖小红娘》播出后口碑分化，部分观众认为改编偏离原著，但也有粉丝力挺杨幂演技。"),
        ],
        "肖战": [
            ("肖战《射雕英雄传：侠之大者》定档春节，徐克执导引期待", "肖战主演、徐克执导的《射雕英雄传：侠之大者》正式定档2025年春节，肖战饰演郭靖引发热议。"),
            ("肖战《藏海传》杀青，与郑晓龙导演合作", "肖战主演古装剧《藏海传》正式杀青，由郑晓龙执导，肖战饰演汪藏海一角，预计2025年播出。"),
            ("肖战商业价值持续走高，多个国际品牌代言", "肖战近年商业代言涵盖多个领域，从偶像成功转型实力派演员，商业价值持续走高。"),
        ],
        "王一博": [
            ("王一博《探索新境》获好评，展现户外探索实力", "王一博与Discovery合作的户外探索纪实节目《探索新境》播出，展现摩托车、攀岩等多面才华。"),
            ("王一博与乐华娱乐合约将到期，去向成焦点", "作为乐华娱乐核心艺人，王一博的合约续约情况持续受到市场关注，直接影响公司股价走向。"),
            ("王一博新片《人鱼》筹备中，程耳执导", "王一博将与导演程耳再度合作新片《人鱼》，此前两人合作的《无名》获得良好口碑。"),
        ],
        "赵丽颖": [
            ("赵丽颖《第二十条》演技获赞，转型实力派里程碑", "赵丽颖在张艺谋执导的《第二十条》中饰演听障母亲，演技获得观众和影评人一致好评。"),
            ("赵丽颖《与凤行》热播，与林更新二搭获好评", "赵丽颖主演的仙侠剧《与凤行》播出后口碑良好，与林更新再度合作引发粉丝回忆。"),
            ("赵丽颖离婚后事业再攀高峰，商业代言不断", "2021年离婚后赵丽颖专注事业，影视作品口碑票房双丰收，商业价值持续攀升。"),
        ],
        "迪丽热巴": [
            ("迪丽热巴多部待播剧引期待，《枭起青壤》备受瞩目", "迪丽热巴与陈星旭合作的《枭起青壤》改编自尾鱼小说，备受粉丝期待。"),
            ("迪丽热巴时尚资源不断，多个奢侈品牌大使", "迪丽热巴持续活跃于时尚领域，代言多个国际奢侈品牌，商业价值位列顶流行列。"),
            ("迪丽热巴《利剑玫瑰》缉毒题材新尝试", "迪丽热巴与金世佳合作的缉毒题材剧《利剑玫瑰》待播，角色类型全新挑战。"),
        ],
        "唐嫣": [
            ("唐嫣《繁花》汪小姐爆红，王家卫赞不绝口", "唐嫣在王家卫执导的《繁花》中饰演汪小姐，演技获得广泛好评，被视为演艺生涯突破性角色。"),
            ("唐嫣《繁花》后商业价值飙升，代言接到手软", "《繁花》播出后唐嫣商业价值大幅攀升，多个品牌争相邀请代言，重回一线女星行列。"),
            ("唐嫣罗晋婚后低调恩爱，娱乐圈模范夫妻", "唐嫣与罗晋2018年结婚，婚后保持低调但偶尔秀恩爱，被视为娱乐圈模范夫妻代表。"),
        ],
        "贾乃亮": [
            ("贾乃亮直播带货创销售纪录，转型成功", "贾乃亮在抖音直播带货中多次创造高销售纪录，成功从演员转型头部主播。"),
            ("贾乃亮与甜馨父女互动上热搜，好爸爸形象深入人心", "贾乃亮与女儿甜馨的互动经常成为热门话题，离婚后以好爸爸形象获得公众好感。"),
            ("贾乃亮综艺感获认可，多档节目常驻嘉宾", "离婚后贾乃亮活跃于多档综艺节目，展现搞笑天赋和综艺感，事业成功转型。"),
        ],
    }

    # 通用新闻模板
    generic_news = [
        ("{}现身活动，状态在线", "{}出席品牌活动，状态十分在线，引来媒体和粉丝关注。"),
        ("{}工作室发声明澄清网络传闻", "{}工作室就近期网络不实传闻发布声明澄清，呼吁理性讨论。"),
        ("{}时尚大片发布，造型引热议", "{}最新时尚大片正式发布，展现独特时尚品味，引发网友热议。"),
    ]

    sources = ["新浪娱乐", "搜狐娱乐", "网易娱乐", "腾讯娱乐", "凤凰网娱乐"]

    # 收集所有新闻
    specific = person_news.get(name, [])
    all_news = specific + generic_news

    random.shuffle(all_news)

    for i in range(min(count, len(all_news))):
        title_template, content_template = all_news[i]
        title = title_template.format(name)
        full_content = content_template.format(name)

        summary_templates = [
            f"{name}近日动态引发关注",
            f"网友热议{name}近况",
            f"{name}相关话题登上热搜",
        ]

        news.append(NewsArticle(
            title=title,
            content=full_content,
            summary=random.choice(summary_templates),
            publish_date=(datetime.now() - timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d"),
            source=random.choice(sources),
            source_url=f"https://example.com/news/{name}/{i}",
            views=random.randint(10000, 1000000),
            likes=random.randint(100, 10000),
            sentiment=random.choice(["positive", "neutral", "neutral"]),
            sentiment_score=random.uniform(-0.2, 0.5),
        ))

    return news


def generate_mock_gossips(name: str) -> list[GossipItem]:
    """生成模拟八卦"""
    gossips = []

    # 从数据库查找
    for gossip_data in GOSSIP_DATABASE:
        if name in gossip_data["names"]:
            gossips.append(GossipItem(
                title=gossip_data["title"],
                content=gossip_data["content"],
                gossip_type=gossip_data["type"],
                date=gossip_data["date"],
                involved_celebrities=gossip_data["names"],
                importance=gossip_data["importance"],
                verified=gossip_data["verified"],
                source_type=DataSourceType.SINA,
                sentiment="negative" if gossip_data["type"] in [GossipType.CHEATING, GossipType.SCANDAL] else "neutral",
                sentiment_score=-0.3 if gossip_data["type"] in [GossipType.CHEATING, GossipType.SCANDAL] else 0.0,
            ))

    return gossips


def generate_mock_relationships(name: str) -> list[Relationship]:
    """生成模拟关系 - 基于真实关系"""
    relationships = []

    # 精确的关系映射（基于公开信息）
    relationship_map = {
        ("罗晋", "唐嫣"): {"type": "配偶", "current": True, "conf": 0.99, "str": 0.95,
                          "desc": "2016年因《锦绣未央》相识，2018年维也纳结婚，2020年育有一女，娱乐圈模范夫妻"},
        ("唐嫣", "罗晋"): {"type": "配偶", "current": True, "conf": 0.99, "str": 0.95,
                          "desc": "2016年因《锦绣未央》相识，2018年维也纳结婚，2020年育有一女"},
        ("贾乃亮", "李小璐"): {"type": "前配偶", "current": False, "conf": 0.99, "str": 0.2,
                            "desc": "2012年结婚，2019年因夜宿门事件离婚，育有一女甜馨"},
        ("李小璐", "贾乃亮"): {"type": "前配偶", "current": False, "conf": 0.99, "str": 0.2,
                            "desc": "2012年结婚，2019年离婚，关系已彻底结束"},
        ("李小璐", "PG One"): {"type": "绯闻对象", "current": False, "conf": 0.9, "str": 0.4,
                             "desc": "2017年底夜宿门事件当事人，关系导致双方事业受损"},
        ("PG One", "李小璐"): {"type": "绯闻对象", "current": False, "conf": 0.9, "str": 0.4,
                             "desc": "2017年底夜宿门事件，导致被封杀"},
        ("王一博", "肖战"): {"type": "搭档", "current": True, "conf": 0.9, "str": 0.75,
                          "desc": "2019年合作《陈情令》，剧后各自发展，CP粉基础庞大"},
        ("肖战", "王一博"): {"type": "搭档", "current": True, "conf": 0.9, "str": 0.75,
                          "desc": "2019年合作《陈情令》，剧后各自发展，CP粉基础庞大"},
        ("杨幂", "迪丽热巴"): {"type": "前同事", "current": False, "conf": 0.95, "str": 0.5,
                            "desc": "同属嘉行传媒时期的前后辈关系，2023年杨幂离开嘉行后关系淡化"},
        ("迪丽热巴", "杨幂"): {"type": "前同事", "current": False, "conf": 0.95, "str": 0.5,
                            "desc": "嘉行传媒时期的前辈与后辈，杨幂曾是公司创始股东"},
        ("杨幂", "赵丽颖"): {"type": "同代竞争", "current": True, "conf": 0.7, "str": 0.4,
                           "desc": "同为85花顶流，长期被媒体和粉丝比较，竞争关系明显"},
        ("赵丽颖", "杨幂"): {"type": "同代竞争", "current": True, "conf": 0.7, "str": 0.4,
                           "desc": "同为85花顶流，粉丝群体经常比较两人作品和商业价值"},
        ("杨幂", "唐嫣"): {"type": "好友", "current": True, "conf": 0.8, "str": 0.6,
                         "desc": "娱乐圈多年好友，曾多次合作，私下关系融洽"},
        ("唐嫣", "杨幂"): {"type": "好友", "current": True, "conf": 0.8, "str": 0.6,
                         "desc": "娱乐圈多年好友，关系稳定"},
        ("杨幂", "肖战"): {"type": "好友", "current": True, "conf": 0.6, "str": 0.4,
                         "desc": "曾公开互动，业内关系友好"},
        ("肖战", "杨幂"): {"type": "好友", "current": True, "conf": 0.6, "str": 0.4,
                         "desc": "业内前辈后辈关系，偶有互动"},
    }

    # 查找关系
    for key, rel_data in relationship_map.items():
        if key[0] == name:
            relationships.append(Relationship(
                person_a=key[0],
                person_b=key[1],
                relation_type=rel_data["type"],
                is_current=rel_data["current"],
                confidence=rel_data["conf"],
                description=rel_data["desc"],
                strength=rel_data["str"],
            ))

    return relationships


def generate_mock_result(name: str) -> ScrapeResult:
    """生成完整的模拟爬取结果"""
    profile = generate_mock_profile(name)

    return ScrapeResult(
        celebrity=profile,
        gossips=generate_mock_gossips(name),
        relationships=generate_mock_relationships(name),
        news_articles=generate_mock_news(name, random.randint(10, 20)),
        comments=generate_mock_comments(name, random.randint(30, 80)),
        social_media_posts=generate_mock_posts(name, random.randint(15, 30)),
        data_completeness=random.uniform(0.85, 0.98),
        last_updated=datetime.now(),
    )


def get_available_celebrities() -> list[str]:
    """获取可用的明星列表"""
    return list(CELEBRITY_DATA.keys())
