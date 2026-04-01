#!/usr/bin/env python3
"""
明星数据更新脚本 - 百度百科 + 微博双源爬取

使用方法:
  python update_weibo_data.py --names 杨幂 赵丽颖
  python update_weibo_data.py --all
"""

import argparse
import json
import os
import re
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from celebrity_scraper.spiders.weibo_deep_spider import (
    WeiboDeepSpider,
    convert_to_social_posts,
)
from celebrity_scraper.models import GossipType, DataSourceType


TOP_CELEBRITIES = [
    "肖战", "王一博", "杨幂", "赵丽颖", "迪丽热巴",
    "唐嫣", "罗晋", "李小璐", "贾乃亮", "PG One",
]

# 已知名人之间的确定关系（人工验证）
KNOWN_RELATIONSHIPS = [
    # 配偶
    {"person_a": "唐嫣", "person_b": "罗晋", "relation_type": "配偶",
     "is_current": True, "description": "2018年结婚", "confidence": 1.0, "strength": 0.9},
    # 前配偶
    {"person_a": "李小璐", "person_b": "贾乃亮", "relation_type": "前配偶",
     "is_current": False, "description": "2012年结婚，2019年离婚", "confidence": 1.0, "strength": 0.7},
    {"person_a": "杨幂", "person_b": "刘恺威", "relation_type": "前配偶",
     "is_current": False, "description": "2014年结婚，2018年离婚", "confidence": 1.0, "strength": 0.7},
    {"person_a": "赵丽颖", "person_b": "冯绍峰", "relation_type": "前配偶",
     "is_current": False, "description": "2018年结婚，2021年离婚", "confidence": 1.0, "strength": 0.7},
    # 绯闻
    {"person_a": "PG One", "person_b": "李小璐", "relation_type": "绯闻",
     "is_current": False, "description": "2017年夜宿门事件", "confidence": 0.95, "strength": 0.8},
    # 对手
    {"person_a": "PG One", "person_b": "贾乃亮", "relation_type": "对手",
     "is_current": True, "description": "夜宿门导致贾乃亮婚姻破裂", "confidence": 0.95, "strength": 0.8},
    # 搭档
    {"person_a": "肖战", "person_b": "王一博", "relation_type": "搭档",
     "is_current": True, "description": "《陈情令》共同主演", "confidence": 1.0, "strength": 0.6},
]


def load_uid_map() -> dict:
    map_path = Path(__file__).parent / "celebrity_scraper" / "weibo_uid_map.json"
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_uid_map(uid_map: dict):
    map_path = Path(__file__).parent / "celebrity_scraper" / "weibo_uid_map.json"
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(uid_map, f, ensure_ascii=False, indent=2)


def get_cookie(args) -> str:
    if args.cookie:
        return args.cookie
    if args.cookie_file:
        return Path(args.cookie_file).read_text(encoding='utf-8').strip()
    env_cookie = os.environ.get('WEIBO_COOKIE', '')
    if env_cookie:
        return env_cookie
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('WEIBO_COOKIE='):
                c = line[len('WEIBO_COOKIE='):].strip()
                if c:
                    return c
    print("未提供 Cookie。使用 --cookie / --cookie-file / .env WEIBO_COOKIE=xxx")
    sys.exit(1)


# ============================================================
# 百度百科 同步爬虫
# ============================================================

BAIKE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def scrape_baike(name: str) -> dict:
    """从百度百科爬取完整资料（同步 requests）"""
    result = {
        'biography': '', 'english_name': '', 'birth_date': None,
        'birth_place': '', 'constellation': '', 'zodiac': '',
        'occupation': [], 'company': '', 'education': '',
        'alma_mater': '', 'height': '', 'weight': '', 'blood_type': '',
        'famous_works': [], 'avatar_url': '', 'sources': [],
        'gossips': [], 'relationships': [],
    }

    url = f'https://baike.baidu.com/item/{quote(name)}'
    try:
        resp = requests.get(url, headers=BAIKE_HEADERS, timeout=15)
        if resp.status_code != 200 or 'lemma-summary' not in resp.text:
            print(f"    百科页面未找到或无效")
            return result
    except Exception as e:
        print(f"    百科请求失败: {e}")
        return result

    soup = BeautifulSoup(resp.text, 'html.parser')
    result['sources'].append(str(resp.url))

    # 1. 简介 - 优先用 meta description，补充 lemma-summary
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        result['biography'] = meta['content'][:500]
    summary_el = soup.select_one('.lemma-summary')
    if summary_el and not result['biography']:
        result['biography'] = summary_el.get_text(separator=' ', strip=True)[:500]

    # 2. 基本信息表（动态 class 名，用 dt/dd 通用匹配）
    _parse_info_table(soup, result)

    # 3. 作品列表（从表格提取）
    _parse_works(soup, result)

    # 4. 人物关系
    _parse_relationships(soup, name, result)

    # 5. 争议/事件
    _parse_controversies(soup, name, result)

    # 6. 头像
    for sel in ['.summary-pic img', '.lemma-pic img', 'img.J-img',
                'div[class*="summary"] img', 'div[class*="lemma"] img[src*="sinaimg"]']:
        img = soup.select_one(sel)
        if img:
            src = img.get('src') or img.get('data-src', '')
            if src and ('sinaimg' in src or 'baidu' in src):
                result['avatar_url'] = src
                break

    return result


def _parse_info_table(soup, result: dict):
    """解析基本信息表格（百度百科动态 class 名，用通用匹配）"""
    # 方法1: 所有 dt/dd 对
    for dt in soup.find_all('dt'):
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        label = re.sub(r'[\s\xa0\u3000]+', '', dt.get_text()).rstrip('：:')
        value = dd.get_text(strip=True)
        if len(label) > 8 or not value:
            continue
        _assign_field(label, value, result)

    # 方法2: th/td 对
    for tr in soup.select('table tr'):
        th = tr.find('th')
        td = tr.find('td')
        if th and td:
            label = th.get_text(strip=True).rstrip('：:')
            value = td.get_text(strip=True)
            if len(label) <= 8 and value:
                _assign_field(label, value, result)


def _assign_field(label: str, value: str, result: dict):
    """将百科字段映射到 result"""
    # 清理标签中的不间断空格和特殊字符
    label = re.sub(r'[\s\xa0\u3000]+', '', label).rstrip('：:')
    if not label or len(label) > 8:
        return
    value = value.strip()

    if '出生日期' in label or label == '出生':
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', value)
        if m:
            result['birth_date'] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        place = re.search(r'([^，。\s]{2,10}(?:省|市|区|县|自治))', value)
        if place:
            result['birth_place'] = place.group(1)
    elif '出生地' in label:
        result['birth_place'] = value
    elif '外文名' in label or '英文名' in label:
        if not result['english_name']:
            result['english_name'] = value.split('、')[0].strip()
    elif '星座' in label:
        result['constellation'] = re.sub(r'\[.*?\]', '', value).strip()
    elif '生肖' in label:
        result['zodiac'] = value
    elif '身高' in label:
        result['height'] = re.sub(r'\[.*?\]', '', value).strip()
    elif '体重' in label:
        result['weight'] = re.sub(r'\[.*?\]', '', value).strip()
    elif '血型' in label:
        result['blood_type'] = value
    elif '职业' in label:
        result['occupation'] = [v.strip() for v in re.split(r'[、,，/]', value) if v.strip()]
    elif '毕业' in label:
        val = re.sub(r'\[.*?\]', '', value).strip()
        result['alma_mater'] = val
        result['education'] = val
    elif '经纪公司' in label or '公司' in label:
        result['company'] = re.sub(r'\[.*?\]', '', value).strip()
    elif '代表作品' in label or '主要作品' in label:
        works = re.findall(r'《([^》]+)》', value)
        if not works:
            works = [w.strip() for w in re.split(r'[、,，]', value) if w.strip()]
        result['famous_works'].extend(works[:20])


def _parse_works(soup, result: dict):
    """从表格和正文中提取作品列表"""
    works = set()

    # 方法1: 从表格中提取《》标题
    for table in soup.find_all('table'):
        header_row = table.find('tr')
        if not header_row:
            continue
        ths = header_row.find_all('th')
        header_texts = [th.get_text(strip=True) for th in ths]
        # 查找包含"作品名称"列的表格
        work_col = None
        for i, ht in enumerate(header_texts):
            if '作品' in ht or '名称' in ht or '节目' in ht:
                work_col = i
                break
        if work_col is None:
            continue
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if len(tds) > work_col:
                text = tds[work_col].get_text(strip=True)
                found = re.findall(r'《([^》]{2,30})》', text)
                if found:
                    works.update(found)
                elif len(text) >= 2:
                    works.add(text)

    # 方法2: 从正文标题为"作品"的section中提取
    for header in soup.find_all(['h2', 'h3']):
        h_text = header.get_text(strip=True)
        if '作品' not in h_text:
            continue
        sibling = header.find_next_sibling()
        for _ in range(15):
            if not sibling or sibling.name in ['h1', 'h2']:
                break
            text = sibling.get_text()
            found = re.findall(r'《([^》]{2,30})》', text)
            works.update(found)
            sibling = sibling.find_next_sibling()

    if works and not result['famous_works']:
        result['famous_works'] = list(works)[:25]


def _looks_like_person_name(text: str) -> bool:
    """判断文本是否像中国人名（2-4个中文字符，无标点/特殊字符）"""
    text = text.strip()
    if not (2 <= len(text) <= 4):
        return False
    return bool(re.fullmatch(r'[\u4e00-\u9fff]{2,4}', text))


def _parse_relationships(soup, name: str, result: dict):
    """解析人物关系（仅从基本信息表和简介中提取，避免正文噪音）"""
    # 优先从 dt/dd 信息表提取关系
    for dt in soup.find_all('dt'):
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        label = re.sub(r'[\s\xa0\u3000]+', '', dt.get_text()).rstrip('：:')
        value = dd.get_text(strip=True)
        if not value:
            continue

        if '配偶' in label or '丈夫' in label or '妻子' in label:
            person = re.sub(r'\[.*?\]', '', value).strip()
            if _looks_like_person_name(person) and person != name:
                result['relationships'].append({
                    'person_a': name, 'person_b': person,
                    'relation_type': '配偶',
                    'is_current': True, 'description': '',
                    'confidence': 0.9, 'strength': 0.8,
                })
        elif '前夫' in label or '前妻' in label:
            person = re.sub(r'\[.*?\]', '', value).strip()
            if _looks_like_person_name(person) and person != name:
                result['relationships'].append({
                    'person_a': name, 'person_b': person,
                    'relation_type': '前配偶',
                    'is_current': False, 'description': '',
                    'confidence': 0.9, 'strength': 0.6,
                })
        elif '子女' in label or '女儿' in label or '儿子' in label:
            # 子女可能有多个，用分隔符拆分
            for part in re.split(r'[、,，/]', value):
                person = re.sub(r'\[.*?\]', '', part).strip()
                if _looks_like_person_name(person) and person != name:
                    result['relationships'].append({
                        'person_a': name, 'person_b': person,
                        'relation_type': '子女',
                        'is_current': True, 'description': '',
                        'confidence': 0.9, 'strength': 0.7,
                    })

    # 从简介中补充（仅匹配紧贴关键词后的人名）
    summary = result.get('biography', '')
    if summary:
        for pattern, rel_type in [
            (r'(?:丈夫|配偶|老公)[是为]\s*([\u4e00-\u9fff]{2,4})', '配偶'),
            (r'(?:前夫|前妻)[是为]\s*([\u4e00-\u9fff]{2,4})', '前配偶'),
        ]:
            for m in re.finditer(pattern, summary):
                person = m.group(1)
                if person != name and not any(
                    r['person_b'] == person for r in result['relationships']
                ):
                    result['relationships'].append({
                        'person_a': name, 'person_b': person,
                        'relation_type': rel_type,
                        'is_current': rel_type != '前配偶',
                        'description': '', 'confidence': 0.7, 'strength': 0.6,
                    })


def _parse_controversies(soup, name: str, result: dict):
    """解析争议/事件章节"""
    # 查找争议相关章节
    controversy_keywords = ['争议', '事件', '人物争议', '负面', '风波']

    for header in soup.find_all(['h2', 'h3']):
        h_text = header.get_text(strip=True)
        if not any(k in h_text for k in controversy_keywords):
            continue

        # 收集该章节的内容
        paragraphs = []
        sibling = header.find_next_sibling()
        while sibling and sibling.name not in ['h1', 'h2']:
            text = sibling.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)
            sibling = sibling.find_next_sibling()

        if paragraphs:
            content = '\n'.join(paragraphs)[:500]

            # 判断八卦类型
            gossip_type = 'other'
            if any(k in content for k in ['出轨', '丑闻']):
                gossip_type = 'cheating'
            elif any(k in content for k in ['离婚']):
                gossip_type = 'divorce'
            elif any(k in content for k in ['恋情', '结婚']):
                gossip_type = 'romance'
            elif any(k in content for k in ['争议', '质疑']):
                gossip_type = 'controversy'

            # 提取时间
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', content)
            date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}" if date_match else None

            result['gossips'].append({
                'title': h_text,
                'content': content,
                'gossip_type': gossip_type,
                'date': date_str,
                'involved_celebrities': [name],
                'importance': 0.8,
                'verified': True,
                'sentiment': 'negative',
            })


# ============================================================
# 跨名人关系提取（简介 + 八卦 + 静态映射）
# ============================================================

def extract_cross_celebrity_relations(output_dir: Path, all_names: list[str]):
    """批量运行后，从简介/八卦中发现跨名人关系，并注入静态关系"""
    name_set = set(all_names)

    # 收集所有数据
    all_data: dict[str, dict] = {}
    for f in sorted(output_dir.glob("*.json")):
        if f.name == "summary.json":
            continue
        d = json.load(open(f, encoding='utf-8'))
        name = d['celebrity']['name']
        all_data[name] = d

    # --- 第一轮：从简介中检测其他名人提及，推断关系类型 ---
    context_keywords = {
        '配偶': ['结婚', '婚礼', '丈夫', '妻子', '老公', '老婆', '官宣恋情'],
        '前配偶': ['离婚', '前夫', '前妻', '协议离婚', '官宣离婚'],
        '绯闻': ['绯闻', '夜宿', '出轨', '亲密', '恋情曝光', '疑似恋情'],
        '搭档': ['合作', '主演', '搭档', '共同出演', '联袂', '携手'],
        '对手': ['矛盾', '不和', '互撕', '冲突', '争议', '封杀'],
    }

    for name, data in all_data.items():
        bio = data['celebrity'].get('biography', '')
        existing_partners = {r['person_b'] for r in data.get('relationships', [])}

        for other_name in name_set:
            if other_name == name or other_name in existing_partners:
                continue
            if other_name not in bio:
                continue

            # 找到提及位置，分析上下文
            idx = bio.find(other_name)
            ctx_before = bio[max(0, idx - 30):idx]
            ctx_after = bio[idx:idx + len(other_name) + 30]

            rel_type = '关联'
            confidence = 0.5
            for rtype, keywords in context_keywords.items():
                if any(k in ctx_before or k in ctx_after for k in keywords):
                    rel_type = rtype
                    confidence = 0.75
                    break

            if rel_type != '关联' or confidence >= 0.5:
                data['relationships'].append({
                    'person_a': name, 'person_b': other_name,
                    'relation_type': rel_type,
                    'is_current': rel_type not in ('前配偶',),
                    'description': f'简介提及: ...{ctx_before[-15:]}{other_name}{ctx_after[len(other_name):15]}...',
                    'confidence': confidence,
                    'strength': 0.6 if rel_type != '关联' else 0.3,
                })

    # --- 第二轮：从八卦事件中发现关系 ---
    for name, data in all_data.items():
        for gossip in data.get('gossips', []):
            involved = gossip.get('involved_celebrities', [])
            for other in involved:
                if other == name or other not in name_set:
                    continue
                existing_partners = {r['person_b'] for r in data['relationships']}
                if other in existing_partners:
                    continue
                gossip_type = gossip.get('gossip_type', 'other')
                rel_map = {
                    'cheating': ('绯闻', 0.85),
                    'divorce': ('前配偶', 0.8),
                    'romance': ('绯闻', 0.7),
                    'controversy': ('对手', 0.7),
                }
                rel_type, conf = rel_map.get(gossip_type, ('关联', 0.5))
                data['relationships'].append({
                    'person_a': name, 'person_b': other,
                    'relation_type': rel_type,
                    'is_current': rel_type not in ('前配偶',),
                    'description': f"八卦: {gossip.get('title', '')}",
                    'confidence': conf,
                    'strength': 0.7,
                })

    # --- 第三轮：注入静态已知关系 ---
    for rel in KNOWN_RELATIONSHIPS:
        a, b = rel['person_a'], rel['person_b']
        if a not in all_data:
            continue
        data = all_data[a]
        existing_partners = {r['person_b'] for r in data['relationships']}
        if b in existing_partners:
            # 用静态数据覆盖/增强已有条目
            for r in data['relationships']:
                if r['person_b'] == b:
                    r['relation_type'] = rel['relation_type']
                    r['is_current'] = rel.get('is_current', True)
                    r['description'] = rel.get('description', '')
                    r['confidence'] = rel.get('confidence', 1.0)
                    r['strength'] = rel.get('strength', 0.7)
                    break
        else:
            data['relationships'].append({
                'person_a': a, 'person_b': b,
                'relation_type': rel['relation_type'],
                'is_current': rel.get('is_current', True),
                'description': rel.get('description', ''),
                'confidence': rel.get('confidence', 1.0),
                'strength': rel.get('strength', 0.7),
            })

    # --- 保存所有文件 ---
    total_rels = 0
    for name, data in all_data.items():
        n = len(data['relationships'])
        data['statistics']['total_relationships'] = n
        total_rels += n

        safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
        fpath = output_dir / f"{safe_name}.json"
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n跨名人关系提取完成: 共 {total_rels} 条关系")


# ============================================================
# 主流程
# ============================================================

def update_celebrity(weibo_spider: WeiboDeepSpider, name: str, uid: str,
                     output_dir: Path, pages: int) -> bool:
    """双源爬取单个明星"""
    # 1. 百度百科
    print(f"  [1/2] 百度百科...")
    baike = scrape_baike(name)
    occ = ', '.join(baike['occupation'][:3])
    works_n = len(baike['famous_works'])
    bio_short = baike['biography'][:60]
    print(f"  [1/2] 百科: {occ} | 作品 {works_n} | 八卦 {len(baike['gossips'])} | {bio_short}...")

    # 2. 微博
    weibo = None
    if uid:
        print(f"  [2/2] 微博 (UID: {uid})...")
        weibo = weibo_spider.scrape_celebrity(name, uid, post_pages=pages)
        if weibo:
            fans = weibo['profile'].get('followers', 0)
            posts_n = len(weibo['posts'])
            print(f"  [2/2] 微博: 粉丝 {fans:,} | 动态 {posts_n} 条")
        else:
            print(f"  [2/2] 微博失败")
    else:
        print(f"  [2/2] 跳过微博")

    # 3. 合并保存
    social_posts = convert_to_social_posts(weibo['posts'], name) if weibo and weibo.get('posts') else []

    celebrity_data = {
        "celebrity": {
            "name": name,
            "english_name": baike.get('english_name', ''),
            "birth_date": baike.get('birth_date'),
            "birth_place": baike.get('birth_place', ''),
            "age": 0,
            "zodiac": baike.get('zodiac', ''),
            "constellation": baike.get('constellation', ''),
            "occupation": baike.get('occupation', []),
            "company": baike.get('company', ''),
            "agency": '',
            "height": baike.get('height', ''),
            "weight": baike.get('weight', ''),
            "blood_type": baike.get('blood_type', ''),
            "biography": baike.get('biography', '')[:500],
            "education": baike.get('education', ''),
            "alma_mater": baike.get('alma_mater', ''),
            "works": [],
            "famous_works": baike.get('famous_works', [])[:20],
            "weibo_id": weibo['profile'].get('id', '') if weibo else '',
            "weibo_followers": weibo['profile'].get('followers', 0) if weibo else 0,
            "avatar_url": baike.get('avatar_url', ''),
            "popularity_score": 0.0,
            "hot_search_count": 0,
            "sources": baike.get('sources', []),
            "updated_at": datetime.now().isoformat(),
        },
        "gossips": baike.get('gossips', []),
        "relationships": baike.get('relationships', []),
        "social_media_posts": [
            {
                "id": p.id, "platform": p.platform, "author": p.author,
                "content": p.content[:300], "likes": p.likes,
                "reposts": p.reposts, "comments": p.comments,
                "publish_time": p.publish_time, "source_url": p.source_url,
                "tags": p.tags[:5], "topics": p.topics[:5],
            }
            for p in social_posts
        ],
        "comments": [],
        "news_articles": [],
        "statistics": {
            "data_completeness": 0.0,
            "total_posts": len(social_posts),
            "total_comments": 0,
            "total_news": 0,
            "total_relationships": len(baike.get('relationships', [])),
            "total_gossips": len(baike.get('gossips', [])),
        },
    }

    # 计算完整度
    c = celebrity_data['celebrity']
    score = 0.0
    if c['biography'] and len(c['biography']) > 20: score += 1
    if c['occupation']: score += 1
    if c['birth_date']: score += 1
    if c['famous_works']: score += 1.5
    if c['weibo_followers'] > 0: score += 0.5
    if len(social_posts) > 10: score += 1.5
    elif len(social_posts) > 0: score += 0.5
    if celebrity_data['relationships']: score += 1
    if celebrity_data['gossips']: score += 1
    celebrity_data['statistics']['data_completeness'] = min(score / 10.0, 1.0)

    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    json_path = output_dir / f"{safe_name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(celebrity_data, f, ensure_ascii=False, indent=2)

    completeness = celebrity_data['statistics']['data_completeness']
    print(f"  保存: {json_path.name} (完整度 {completeness:.0%})")
    return True


def main():
    parser = argparse.ArgumentParser(description='明星数据更新（百度百科+微博）')
    parser.add_argument('--cookie', type=str, help='微博 Cookie')
    parser.add_argument('--cookie-file', type=str, help='Cookie 文件路径')
    parser.add_argument('--names', nargs='+', help='指定明星')
    parser.add_argument('--all', action='store_true', help='更新全部')
    parser.add_argument('--validate', action='store_true', help='仅验证 Cookie')
    parser.add_argument('--output-dir', type=str, default='celebrity_scraper/data')
    parser.add_argument('--pages', type=int, default=3, help='微博页数')
    args = parser.parse_args()

    cookie = get_cookie(args)
    weibo_spider = WeiboDeepSpider(cookie)

    print("验证 Cookie...")
    if not weibo_spider.validate_cookie():
        print("Cookie 无效或已过期!")
        sys.exit(1)
    print("Cookie 有效!")

    if args.validate:
        return

    uid_map = load_uid_map()
    names = TOP_CELEBRITIES if args.all else args.names
    if not names:
        print("请指定 --names 或 --all")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    success = fail = 0
    skipped = []

    for i, name in enumerate(names, 1):
        uid = uid_map.get(name, "")
        if not uid:
            print(f"\n[{i}/{len(names)}] 跳过 {name}: 无 UID")
            skipped.append(name)
            continue

        print(f"\n{'='*60}")
        print(f"[{i}/{len(names)}] {name}")
        print(f"{'='*60}")

        try:
            update_celebrity(weibo_spider, name, uid, output_dir, args.pages)
            success += 1
        except Exception as e:
            print(f"  异常: {e}")
            fail += 1

        if i < len(names):
            delay = random.uniform(3, 6)
            print(f"  等待 {delay:.1f}s...")
            time.sleep(delay)

    save_uid_map(uid_map)

    # 跨名人关系提取
    print(f"\n{'='*60}")
    print("跨名人关系提取...")
    extract_cross_celebrity_relations(output_dir, names)

    summary = {
        "scraped_at": datetime.now().isoformat(),
        "mode": "baike+weibo",
        "results": {"success": success, "failed": fail, "skipped": skipped},
    }
    with open(output_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"完成! 成功: {success} | 失败: {fail} | 跳过: {len(skipped)}")
    if skipped:
        print(f"跳过: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
