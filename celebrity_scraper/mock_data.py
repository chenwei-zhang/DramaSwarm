# -*- coding: utf-8 -*-
"""
模拟数据生成器 - 用于测试和演示
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


# 明星基础数据 - 完整版
CELEBRITY_DATA = {
    "肖战": {
        "english_name": "Xiao Zhan",
        "birth_date": "1991-10-05",
        "birth_place": "重庆市",
        "constellation": "天秤座",
        "occupation": ["演员", "歌手"],
        "company": "哇唧唧哇娱乐",
        "biography": "肖战，中国内地影视男演员、歌手。2015年，以选手身份参加浙江卫视才艺养成选秀节目《燃烧吧少年》，最终以X玖少年团成员身份出道。2019年，因出演古装仙侠剧《陈情令》魏无羡一角而获得广泛关注。",
        "famous_works": ["陈情令", "斗罗大陆", "王牌部队", "梦中的那片海", "骄阳伴我", "射雕英雄传侠之大者"],
        "weibo_followers": 30000000,
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
        "biography": "王一博，中国内地男演员、歌手、主持人、职业摩托车赛车手。2014年，以UNIQ组合成员身份正式出道。2019年，主演古装仙侠剧《陈情令》蓝忘机一角而走红。",
        "famous_works": ["陈情令", "有翡", "风起洛阳", "无名", "长空之王", "热烈"],
        "weibo_followers": 40000000,
        "height": "180cm",
        "zodiac": "牛"
    },
    "杨幂": {
        "english_name": "Yang Mi",
        "birth_date": "1986-09-12",
        "birth_place": "北京市",
        "constellation": "处女座",
        "occupation": ["演员", "歌手", "制片人"],
        "company": "嘉行传媒",
        "biography": "杨幂，中国内地影视女演员、流行乐歌手、影视制片人。2005年，杨幂考入北京电影学院表演系。2006年，因出演金庸武侠剧《神雕侠侣》而崭露头角。2011年，凭借穿越剧《宫》获得广泛关注。",
        "famous_works": ["宫", "仙剑奇侠传三", "古剑奇谭", "三生三世十里桃花", "斛珠夫人", "爱的二八定律"],
        "weibo_followers": 60000000,
        "height": "166cm",
        "zodiac": "虎"
    },
    "赵丽颖": {
        "english_name": "Zhao Liying",
        "birth_date": "1987-10-16",
        "birth_place": "河北省廊坊市",
        "constellation": "天秤座",
        "occupation": ["演员"],
        "company": "",
        "biography": "赵丽颖，中国内地影视女演员。2006年，因获得雅虎搜星比赛冯小刚组冠军而进入演艺圈。2013年，主演古装剧《陆贞传奇》获得关注。2015年，主演仙侠剧《花千骨》打破中国内地周播剧收视纪录。",
        "famous_works": ["陆贞传奇", "花千骨", "楚乔传", "知否知否应是绿肥红瘦", "风吹半夏", "与凤行"],
        "weibo_followers": 50000000,
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
        "biography": "迪丽热巴，中国内地影视女演员。2013年，因主演个人首部电视剧《阿娜尔罕》而出道。2015年，凭借电视剧《克拉恋人》获得国剧盛典最受欢迎新人女演员奖。2017年，主演古装剧《三生三世十里桃花》凤九一角而获得更高人气。",
        "famous_works": ["克拉恋人", "漂亮的李慧珍", "三生三世十里桃花", "长歌行", "与君初相识", "安乐传"],
        "weibo_followers": 70000000,
        "height": "168cm",
        "zodiac": "猴"
    },
    "唐嫣": {
        "english_name": "Tiffany Tang",
        "birth_date": "1983-12-06",
        "birth_place": "上海市",
        "constellation": "射手座",
        "occupation": ["演员", "歌手"],
        "company": "",
        "biography": "唐嫣，中国内地影视女演员。2004年，作为奥运宝贝参与雅典奥运会闭幕式演出。2009年，因主演古装仙侠剧《仙剑奇侠传三》获得关注。2015年，主演的爱情剧《何以笙箫默》播出收视亮眼。",
        "famous_works": ["仙剑奇侠传三", "夏家三千金", "何以笙箫默", "锦绣未央", "燕云台", "繁花"],
        "weibo_followers": 35000000,
        "height": "172cm",
        "zodiac": "猪"
    },
    "罗晋": {
        "english_name": "Luo Jin",
        "birth_date": "1981-11-30",
        "birth_place": "江西省宜春市铜鼓县",
        "constellation": "射手座",
        "occupation": ["演员"],
        "company": "",
        "biography": "罗晋，中国内地男演员。2010年，主演历史剧《三国》进入观众视野。2012年，主演古装剧《王的女人》。2015年，主演电视剧《锦绣未央》与唐嫣相识相恋。",
        "famous_works": ["锦绣未央", "归去来", "鹤唳华亭", "幸福到万家", "天下长河", "埃博拉前线"],
        "weibo_followers": 20000000,
        "height": "178cm",
        "zodiac": "鸡"
    },
    "李小璐": {
        "english_name": "Li Xiaolu",
        "birth_date": "1981-09-30",
        "birth_place": "安徽省安庆市",
        "constellation": "天秤座",
        "occupation": ["演员", "歌手"],
        "company": "",
        "biography": "李小璐，中国内地影视女演员、流行乐歌手。1998年，出演剧情片《天浴》获得第35届台湾电影金马奖最佳女主角奖，成为最年轻的金马影后。2012年，主演的家庭情感剧《当婆婆遇上妈》获得高收视。",
        "famous_works": ["天浴", "都是天使惹的祸", "奋斗", "当婆婆遇上妈", "鹿鼎记"],
        "weibo_followers": 20000000,
        "height": "163cm",
        "zodiac": "鸡"
    },
    "贾乃亮": {
        "english_name": "Jia Nailiang",
        "birth_date": "1984-04-12",
        "birth_place": "黑龙江省哈尔滨市",
        "constellation": "白羊座",
        "occupation": ["演员", "歌手"],
        "company": "",
        "biography": "贾乃亮，中国内地影视男演员、流行乐歌手。毕业于北京电影学院表演系。2012年，主演的都市家庭剧《保姆妈妈》播出。2014年，主演的都市家庭剧《产科男医生》获得关注。",
        "famous_works": ["当婆婆遇上妈", "产科男医生", "偏偏喜欢你", "煮妇神探", "推手"],
        "weibo_followers": 15000000,
        "height": "181cm",
        "zodiac": "鼠"
    },
    "PG One": {
        "english_name": "PG One",
        "birth_date": "1992-05-15",
        "birth_place": "黑龙江省哈尔滨市",
        "constellation": "金牛座",
        "occupation": ["说唱歌手", "词曲创作人"],
        "company": "",
        "biography": "PG One，本名王昊，中国内地说唱歌手。2017年，参加爱奇艺Hip-Hop音乐选秀节目《中国有嘻哈》，获得总决赛冠军。2017年底，因与李小璐的夜宿门事件引发争议，随后逐渐淡出主流视野。",
        "famous_works": ["中国有嘻哈", "圣诞歌", "Rocket"],
        "weibo_followers": 500000,
        "height": "178cm",
        "zodiac": "猴"
    },
}

# 八卦事件数据库
GOSSIP_DATABASE = [
    {
        "names": ["李小璐", "贾乃亮", "PG One"],
        "type": GossipType.CHEATING,
        "title": "李小璐贾乃亮婚姻危机事件",
        "content": "2017年底，李小璐被拍到与说唱歌手PG One深夜牵手，引发网友猜测。随后贾乃亮发文表示相信妻子，但两人婚姻出现裂痕。2019年，两人宣布离婚。该事件被称为夜宿门，是2017年娱乐圈最大的八卦之一。",
        "summary": "2017年底李小璐与PG One的夜宿门事件，导致其与贾乃亮的婚姻破裂，最终于2019年离婚。",
        "date": "2017-12-29",
        "importance": 0.95,
        "verified": True
    },
    {
        "names": ["Angelababy", "黄晓明"],
        "type": GossipType.DIVORCE,
        "title": "Angelababy黄晓明离婚",
        "content": "2022年1月，Angelababy与黄晓明宣布结束七年婚姻，双方表示未来将共同抚养孩子小海绵。两人于2015年在上海举办世纪婚礼，被誉为娱乐圈金童玉女。",
        "summary": "2022年1月，Angelababy与黄晓明官宣离婚，结束七年婚姻。",
        "date": "2022-01-28",
        "importance": 0.9,
        "verified": True
    },
    {
        "names": ["吴亦凡"],
        "type": GossipType.SCANDAL,
        "title": "吴亦凡性侵事件",
        "content": "2021年7月，都美竹发文指控吴亦凡涉嫌性侵等多起不当行为，引发社会广泛关注。随后吴亦凡被刑事拘留，2022年一审被判有期徒刑十三年。该事件导致多个品牌解约。",
        "summary": "2021年都美竹指控吴亦凡性侵，导致其被刑拘，2022年一审被判十三年。",
        "date": "2021-07-31",
        "importance": 1.0,
        "verified": True
    },
    {
        "names": ["郑爽"],
        "type": GossipType.SCANDAL,
        "title": "郑爽代孕弃养事件",
        "content": "2021年1月，郑爽前男友张恒发文揭露郑爽在美国代孕两个孩子，并欲弃养，引发社会巨大争议。该事件导致郑爽遭到全网抵制，多部作品被下架，演艺事业基本终结。",
        "summary": "2021年郑爽被曝代孕并欲弃养，引发全网抵制，演艺事业基本终结。",
        "date": "2021-01-18",
        "importance": 0.95,
        "verified": True
    },
    {
        "names": ["汪峰", "章子怡"],
        "type": GossipType.DIVORCE,
        "title": "汪峰章子怡离婚",
        "content": "2023年10月，汪峰与章子怡宣布结束八年婚姻，双方表示是以和平方式分开，将共同抚养孩子。两人于2015年结婚，育有一女。",
        "summary": "2023年10月，汪峰与章子怡官宣离婚，结束八年婚姻。",
        "date": "2023-10-23",
        "importance": 0.85,
        "verified": True
    },
    {
        "names": ["赵丽颖", "冯绍峰"],
        "type": GossipType.DIVORCE,
        "title": "赵丽颖冯绍峰离婚",
        "content": "2021年4月，赵丽颖与冯绍峰官宣离婚，结束两年多的婚姻。两人于2018年结婚，婚后育有一子。声明表示双方是和平分手，未来将共同抚养孩子。",
        "summary": "2021年4月，赵丽颖与冯绍峰官宣离婚，结束两年多婚姻。",
        "date": "2021-04-23",
        "importance": 0.85,
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

    post_templates = [
        "今天的拍摄很顺利，感谢大家的支持！",
        "新作品即将上线，敬请期待！",
        "工作花絮分享~",
        "感谢粉丝们的生日祝福！",
        "今天的阳光真好☀️",
        "录制综艺节目中...",
        "新剧开机，加油！",
        "公益活动，传递正能量",
        "后台准备中💪",
        "收工啦，晚安！",
        "杂志拍摄完成，期待正片",
        "新戏角色挑战，正在努力中",
        "久违的假期，好好休息",
        "感谢品牌方的邀请",
        "剧组杀青啦！",
        "路演现场见，不见不散",
        "新歌听听看，希望大家喜欢",
        "健身打卡第N天",
        "今天的夕阳很美",
        "努力成为更好的自己",
        "感恩相遇，一路同行",
        "工作日常记录",
        "享受当下，不负时光",
        "期待与大家再次见面",
    ]

    hashtags = [
        ["工作", "努力"],
        ["新剧", "期待"],
        ["日常", "分享"],
        ["感恩", "粉丝"],
        ["正能量", "公益"],
        ["杀青", "新戏"],
        ["健身", "运动"],
        ["生活", "记录"],
    ]

    # 随机打乱并选择
    selected_posts = random.sample(post_templates, min(count, len(post_templates)))

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
        "支持{}！加油💪",
        "{}好棒！",
        "期待新作品！",
        "从XX剧就开始喜欢你了",
        "{}真好看",
        "一直支持",
        "加油鸭！",
        "今天也很帅气",
        "新歌/新剧什么时候出？",
        "爱了爱了",
        "{}的演技越来越好了",
        "期待！",
        "{}永远的神",
        "支持到底",
        "从XX年开始追的粉",
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
            sentiment=random.choice(["positive", "positive", "positive", "neutral"]),
            sentiment_score=random.uniform(0.3, 0.9),
        )
        comments.append(comment)

    return comments


def generate_mock_news(name: str, count: int = 15) -> list[NewsArticle]:
    """生成模拟新闻"""
    news = []

    news_templates = [
        ("{}现身机场，身穿休闲装状态佳", "{}今日现身首都机场，身穿简约休闲装，状态看起来十分不错，引来粉丝围观拍照。"),
        ("{}新剧官宣，粉丝期待值拉满", "{}新剧正式官宣，与实力派演员合作，引发粉丝热烈讨论，期待值拉满。"),
        ("{}参加活动，与粉丝互动温馨", "{}出席品牌活动现场，与粉丝互动十分温馨，引发网友热议。"),
        ("{}工作室发声明澄清传闻", "{}工作室今日发布官方声明，就近期网络传闻进行澄清，呼吁不信谣不传谣。"),
        ("{}品牌代言曝光，商业价值持续走高", "{}新代言正式曝光，与多个国际大牌合作，商业价值持续走高。"),
        ("{}综艺路透，录制状态轻松愉快", "{}综艺节目录制现场路透曝光，状态轻松愉快，引发粉丝期待。"),
        ("{}晒生活照，引发网友热议", "{}在社交媒体晒出生活照，展现真实一面，引发网友热议和点赞。"),
        ("{}获奖感言：感谢一路支持", "{}在颁奖典礼上发表获奖感言，感谢粉丝和团队一路支持，场面温馨感人。"),
        ("{}公益行动，传递正能量", "{}参与公益活动，用实际行动传递正能量，获得网友一致好评。"),
        ("{}时尚大片发布，展现多面魅力", "{}最新时尚大片正式发布，展现不同以往的多面魅力，引发时尚圈关注。"),
        ("{}新片开机，挑战全新角色", "{}主演的新片正式开机，此次将挑战与以往完全不同的角色类型，引发期待。"),
        ("{}登封面，气场全开", "{}登上某时尚杂志封面，大片造型气场全开，展现独特时尚品味。"),
        ("{}演唱会门票秒空", "{}巡回演唱会门票开票即秒空，展现强大票房号召力。"),
        ("{}做客综艺，爆料趣事", "{}做客某综艺节目，现场爆料拍摄趣事，引发观众爆笑。"),
        ("{}化身推荐官，助力家乡", "{}成为家乡旅游推荐官，发文助力家乡发展，获网友点赞。"),
    ]

    sources = ["新浪娱乐", "搜狐娱乐", "网易娱乐", "腾讯娱乐", "凤凰网娱乐"]

    # 随机打乱模板顺序，避免每次生成的新闻顺序相同
    shuffled_templates = news_templates.copy()
    random.shuffle(shuffled_templates)

    for i in range(min(count, len(shuffled_templates))):
        title, content = shuffled_templates[i]
        title = title.format(name)
        full_content = content.format(name)

        # 生成不同的摘要，不是content的截断
        summary_templates = [
            f"{name}近日活动引发关注",
            f"{name}新动态曝光",
            f"网友热议{name}近况",
            f"{name}相关话题上热搜",
            f"{name}成为焦点",
        ]
        summary = random.choice(summary_templates)

        news.append(NewsArticle(
            title=title,
            content=full_content,
            summary=summary,
            publish_date=(datetime.now() - timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d"),
            source=random.choice(sources),
            source_url=f"https://example.com/news/{i}",
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

    # 为有作品的明星添加通用八卦
    if not gossips and name in CELEBRITY_DATA:
        works = CELEBRITY_DATA[name].get("famous_works", [])
        if works:
            gossips.append(GossipItem(
                title=f"{name}新剧《{works[0]}》热播",
                content=f"{name}主演的新剧《{works[0]}》正在热播，演技获得观众好评，话题度持续走高。",
                gossip_type=GossipType.OTHER,
                date=(datetime.now() - timedelta(days=random.randint(10, 60))).strftime("%Y-%m-%d"),
                involved_celebrities=[name],
                importance=0.6,
                verified=True,
                source_type=DataSourceType.SINA,
                sentiment="positive",
                sentiment_score=0.5,
            ))

    return gossips


def generate_mock_relationships(name: str) -> list[Relationship]:
    """生成模拟关系"""
    relationships = []

    # 定义关系映射
    relationship_map = {
        ("罗晋", "唐嫣"): ("配偶", True, 0.95, "2016年拍戏相识，2018年维也纳结婚"),
        ("唐嫣", "罗晋"): ("配偶", True, 0.95, "2016年拍戏相识，2018年维也纳结婚"),
        ("贾乃亮", "李小璐"): ("前任", False, 0.95, "2012年结婚，2019年离婚"),
        ("李小璐", "贾乃亮"): ("前任", False, 0.95, "2012年结婚，2019年离婚"),
        ("王一博", "肖战"): ("搭档", True, 0.85, "《陈情令》合作主演"),
        ("肖战", "王一博"): ("搭档", True, 0.85, "《陈情令》合作主演"),
    }

    # 检查是否在关系映射中
    for key, (rel_type, is_current, conf, desc) in relationship_map.items():
        if key[0] == name:
            relationships.append(Relationship(
                person_a=key[0],
                person_b=key[1],
                relation_type=rel_type,
                is_current=is_current,
                confidence=conf,
                description=desc,
                strength=0.8 if is_current else 0.3,
            ))

    # 随机生成一些合作关系
    celebs = list(CELEBRITY_DATA.keys())
    for other_name in celebs:
        if other_name != name and len(relationships) < 5:
            if random.random() < 0.15:
                relationships.append(Relationship(
                    person_a=name,
                    person_b=other_name,
                    relation_type=random.choice(["合作", "好友", "同剧演员"]),
                    is_current=True,
                    confidence=0.7,
                    description=f"曾合作过影视作品",
                    strength=0.5,
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
        data_completeness=random.uniform(0.8, 0.98),
        last_updated=datetime.now(),
    )


def get_available_celebrities() -> list[str]:
    """获取可用的明星列表"""
    return list(CELEBRITY_DATA.keys())
