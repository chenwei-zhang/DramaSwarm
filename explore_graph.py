# -*- coding: utf-8 -*-
"""
知识图谱交互式探索工具

用法:
  python explore_graph.py                    # 交互模式
  python explore_graph.py 杨幂                # 查看某人
  python explore_graph.py path 杨幂 PG One    # 查找路径
  python explore_graph.py stats              # 统计信息
"""

import sys
import json
from swarmsim.graph import KnowledgeGraph


def load_graph() -> KnowledgeGraph:
    """加载知识图谱"""
    kg = KnowledgeGraph()
    stats = kg.load_from_json_dir("celebrity_scraper/data")
    print(f"✅ 知识图谱已加载: {stats['celebrities']}位明星, "
          f"{stats['relationships']}条关系, {stats['gossips']}个八卦事件, "
          f"{stats['news']}条新闻")
    return kg


def show_stats(kg: KnowledgeGraph):
    """显示统计信息"""
    info = kg.get_stats()
    print(f"\n{'='*50}")
    print(f"  知识图谱统计")
    print(f"{'='*50}")
    print(f"  总节点数: {info['total_nodes']}")
    print(f"  总边数:   {info['total_edges']}")
    print(f"\n  节点类型:")
    for t, c in info['node_types'].items():
        print(f"    {t}: {c}")
    print(f"\n  边类型:")
    for t, c in info['edge_types'].items():
        print(f"    {t}: {c}")
    print(f"\n  明星列表: {', '.join(info['celebrities'])}")


def show_person(kg: KnowledgeGraph, name: str):
    """查看某人的详细图谱信息"""
    if name not in kg.celebrity_names:
        # 模糊匹配
        candidates = [n for n in kg.celebrity_names if name in n]
        if candidates:
            name = candidates[0]
        else:
            print(f"❌ 未找到 '{name}'，可用: {', '.join(sorted(kg.celebrity_names))}")
            return

    print(f"\n{'='*50}")
    print(f"  {name} 的知识图谱档案")
    print(f"{'='*50}")

    # 直接关系
    neighbors = kg.get_social_neighborhood(name, max_depth=1)
    if neighbors:
        print(f"\n  【直接关系】({len(neighbors)}人)")
        for n in neighbors:
            types = "、".join(n['relation_types']) if n['relation_types'] else "关联"
            print(f"    {n['name']} — {types}")
    else:
        print(f"\n  【直接关系】无")

    # 二度连接
    neighbors_2 = kg.get_social_neighborhood(name, max_depth=2)
    second = [n for n in neighbors_2 if n['depth'] == 2]
    if second:
        print(f"\n  【二度连接】({len(second)}人)")
        names = [n['name'] for n in second]
        print(f"    {', '.join(names)}")

    # 关联事件
    events = kg.get_related_events(name)
    if events:
        print(f"\n  【关联事件】({len(events)}条)")
        for e in events:
            sentiment_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(e['sentiment'], "⚪")
            print(f"    {sentiment_icon} [{e['type']}] {e['title']} (重要度:{e['importance']:.1f})")

    # 详细关系
    print(f"\n  【关系详情】")
    for n in neighbors:
        rels = kg.get_relationship_context(name, n['name'])
        for r in rels:
            current = "✅" if r.get('is_current') else "❌"
            print(f"    {current} {n['name']}: {r.get('relation_type','?')} "
                  f"(强度:{r.get('strength',0):.2f}, 置信度:{r.get('confidence',0):.2f})")
            desc = r.get('description', '')
            if desc:
                print(f"         {desc}")

    # GraphRAG 上下文（agent 会看到的）
    ctx = kg.to_context_string(name, max_chars=500)
    print(f"\n  【Agent 上下文】")
    print(f"    {ctx}")


def show_path(kg: KnowledgeGraph, name_a: str, name_b: str):
    """查找两人之间的路径"""
    path = kg.find_connection_path(name_a, name_b)
    if not path:
        print(f"❌ 未找到 {name_a} → {name_b} 的路径")
        return

    print(f"\n{'='*50}")
    print(f"  {name_a} → {name_b} 的关系路径")
    print(f"{'='*50}")

    for i, node in enumerate(path):
        ntype = node['type']
        label = node.get('name', '') or node.get('title', '')

        if ntype == 'celebrity':
            icon = "👤"
        elif ntype == 'gossip':
            icon = "🔥"
        else:
            icon = "📰"

        if i == 0:
            print(f"    {icon} {label}")
        else:
            # 找关系类型
            prev = path[i-1]
            prev_id = prev['id']
            curr_id = node['id']
            edge_info = ""
            for u, v, key, data in kg.graph.edges(data=True, keys=True):
                if (u == prev_id and v == curr_id) or (u == curr_id and v == prev_id):
                    if data.get('edge_type') == 'relationship':
                        edge_info = f"({data.get('relation_type', '?')})"
                        break
                    elif data.get('edge_type') == 'involved_in':
                        edge_info = "(参与事件)"
                        break
            print(f"    {'→':>4} [{edge_info}] {icon} {label}")

    print(f"\n  路径长度: {len(path)-1} 跳")


def show_impact(kg: KnowledgeGraph, name: str, event: str):
    """评估事件对某人的影响"""
    impact = kg.get_event_impact(event, name)
    print(f"\n{'='*50}")
    print(f"  事件影响评估")
    print(f"{'='*50}")
    print(f"  事件: {event}")
    print(f"  对 {name} 的影响:")
    print(f"    严重度增量: +{impact['severity_delta']:.2f}")
    if impact['affected_relationships']:
        print(f"    受影响的关系:")
        for r in impact['affected_relationships']:
            print(f"      {r['name']} ({r['relation_type']}): 影响 +{r['impact']:.2f}")
    else:
        print(f"    未检测到直接影响的关系")


def interactive_mode(kg: KnowledgeGraph):
    """交互式探索"""
    print("\n" + "="*50)
    print("  知识图谱交互式探索")
    print("  输入人名查看档案，或输入命令:")
    print("  stats    - 统计信息")
    print("  path A B - 查找路径")
    print("  impact 姓名 事件 - 评估影响")
    print("  list     - 列出所有明星")
    print("  quit     - 退出")
    print("="*50)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input == "quit":
            print("再见！")
            break
        elif user_input == "stats":
            show_stats(kg)
        elif user_input == "list":
            print(f"  明星: {', '.join(sorted(kg.celebrity_names))}")
        elif user_input.startswith("path "):
            parts = user_input[5:].strip().split()
            if len(parts) >= 2:
                show_path(kg, parts[0], parts[1])
            else:
                print("  用法: path 名字A 名字B")
        elif user_input.startswith("impact "):
            parts = user_input[7:].strip().split(None, 1)
            if len(parts) >= 2:
                show_impact(kg, parts[0], parts[1])
            else:
                print("  用法: impact 姓名 事件描述")
        elif user_input in kg.celebrity_names:
            show_person(kg, user_input)
        else:
            # 模糊匹配
            candidates = [n for n in kg.celebrity_names if user_input in n]
            if len(candidates) == 1:
                show_person(kg, candidates[0])
            elif len(candidates) > 1:
                print(f"  多个匹配: {', '.join(candidates)}，请更精确输入")
            else:
                print(f"  未找到 '{user_input}'，输入 list 查看所有明星")


def main():
    kg = load_graph()

    if len(sys.argv) == 1:
        interactive_mode(kg)
    elif sys.argv[1] == "stats":
        show_stats(kg)
    elif sys.argv[1] == "path" and len(sys.argv) >= 4:
        show_path(kg, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "impact" and len(sys.argv) >= 4:
        show_impact(kg, sys.argv[2], " ".join(sys.argv[3:]))
    else:
        name = sys.argv[1]
        show_person(kg, name)


if __name__ == "__main__":
    main()
