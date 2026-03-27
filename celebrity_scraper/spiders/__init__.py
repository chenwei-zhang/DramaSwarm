"""Spider modules"""

from .baidu_baike import BaiduBaikeSpider
from .weibo import WeiboSpider
from .zhihu import ZhihuSpider
from .douban import DoubanSpider
from .news import EntertainmentNewsSpider

__all__ = [
    "BaiduBaikeSpider",
    "WeiboSpider",
    "ZhihuSpider",
    "DoubanSpider",
    "EntertainmentNewsSpider"
]
