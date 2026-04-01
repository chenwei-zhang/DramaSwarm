"""Spider modules"""

from .baidu_baike import BaiduBaikeSpider
from .weibo import WeiboSpider
from .weibo_deep_spider import WeiboDeepSpider
from .zhihu import ZhihuSpider
from .douban import DoubanSpider
from .news import EntertainmentNewsSpider

__all__ = [
    "BaiduBaikeSpider",
    "WeiboSpider",
    "WeiboDeepSpider",
    "ZhihuSpider",
    "DoubanSpider",
    "EntertainmentNewsSpider"
]
