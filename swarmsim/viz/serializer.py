# -*- coding: utf-8 -*-
"""
Graph Serializer - networkx → D3.js JSON 转换

将 KnowledgeGraph 的 MultiDiGraph 转换为前端 D3.js 可消费的 node-link 格式。
"""

from __future__ import annotations

import math
from typing import Any

from swarmsim.graph import KnowledgeGraph


def graph_to_d3(
    kg: KnowledgeGraph,
    filter_type: str = "celebrity",
    name: str | None = None,
    depth: int = 2,
) -> dict:
    """
    将知识图谱转换为 D3.js 力导向图所需的 node-link JSON。

    Args:
        kg: KnowledgeGraph 实例
        filter_type: "celebrity" (仅名人+关系) | "all" (全部)
        name: 当提供时，返回此人的 BFS 邻域子图
        depth: BFS 深度 (1-3)

    Returns:
        {"nodes": [...], "edges": [...]}
    """
    g = kg.graph

    # 收集要包含的节点 ID
    if name:
        target_ids = _bfs_node_ids(g, name, depth)
    elif filter_type == "celebrity":
        target_ids = {nid for nid, d in g.nodes(data=True) if d.get("node_type") == "celebrity"}
    else:  # all
        target_ids = set(g.nodes())

    # 构建节点列表
    nodes = []
    for nid in target_ids:
        data = dict(g.nodes[nid])
        node_type = data.get("node_type", "unknown")

        node = {
            "id": nid,
            "type": node_type,
            "radius": _node_radius(data),
        }

        # 类型特定属性
        if node_type == "celebrity":
            node["name"] = data.get("name", "")
            node["occupation"] = data.get("occupation", [])
            node["company"] = data.get("company", "")
            node["famous_works"] = data.get("famous_works", [])
            node["weibo_followers"] = data.get("weibo_followers", 0)
        elif node_type == "gossip":
            node["title"] = data.get("title", "")
            node["gossip_type"] = data.get("gossip_type", "other")
            node["importance"] = data.get("importance", 0.5)
            node["sentiment"] = data.get("sentiment", "neutral")
        elif node_type == "news":
            node["title"] = data.get("title", "")
            node["source"] = data.get("source", "")
            node["sentiment"] = data.get("sentiment", "neutral")

        nodes.append(node)

    # 构建边列表
    target_id_set = target_ids  # set for fast lookup
    edges = []
    seen_pairs = set()

    for u, v, key, data in g.edges(data=True, keys=True):
        if u not in target_id_set or v not in target_id_set:
            continue

        edge_type = data.get("edge_type", "unknown")

        # relationship 边去重：双向边仅保留一条 (source < target)
        if edge_type == "relationship":
            pair = (min(u, v), max(u, v))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

        edge = {
            "source": u,
            "target": v,
            "edge_type": edge_type,
        }

        # 类型特定属性
        if edge_type == "relationship":
            edge["relation_type"] = data.get("relation_type", "")
            edge["strength"] = data.get("strength", 0.5)
            edge["confidence"] = data.get("confidence", 0.5)
            edge["is_current"] = data.get("is_current", True)
            edge["description"] = data.get("description", "")
        elif edge_type == "involved_in":
            edge["role"] = data.get("role", "mentioned")
        elif edge_type == "simulation_event":
            edge["action_type"] = data.get("action_type", "")
            edge["turn"] = data.get("turn", 0)
            edge["severity"] = data.get("severity", 0.5)
            edge["weight"] = data.get("weight", 1.0)

        edges.append(edge)

    return {"nodes": nodes, "edges": edges}


def _bfs_node_ids(g, name: str, depth: int) -> set[str]:
    """从指定名人节点 BFS 收集节点 ID"""
    start = f"celebrity:{name}"
    if not g.has_node(start):
        return set()

    visited = {start}
    current_level = [start]

    for _ in range(depth):
        next_level = []
        for nid in current_level:
            for succ in g.successors(nid):
                if succ not in visited:
                    visited.add(succ)
                    next_level.append(succ)
            for pred in g.predecessors(nid):
                if pred not in visited:
                    visited.add(pred)
                    next_level.append(pred)
        current_level = next_level

    return visited


def _node_radius(data: dict) -> float:
    """根据节点属性计算显示半径"""
    node_type = data.get("node_type", "unknown")

    if node_type == "celebrity":
        followers = data.get("weibo_followers", 0) or 0
        if followers > 0:
            return 18 + math.log10(max(followers, 1e4)) * 3
        return 20
    elif node_type == "gossip":
        return 10 + data.get("importance", 0.5) * 10
    else:  # news
        return 8


def person_detail(kg: KnowledgeGraph, name: str) -> dict:
    """获取名人详情（合并节点属性 + 邻域 + 事件）"""
    node_id = f"celebrity:{name}"
    if not kg.graph.has_node(node_id):
        return {}

    data = dict(kg.graph.nodes[node_id])

    result = {
        "name": data.get("name", name),
        "occupation": data.get("occupation", []),
        "company": data.get("company", ""),
        "biography": data.get("biography", ""),
        "famous_works": data.get("famous_works", []),
        "weibo_followers": data.get("weibo_followers", 0),
        "neighbors": kg.get_social_neighborhood(name, max_depth=1),
        "events": kg.get_related_events(name),
    }

    # 关系详情
    relationships = []
    for neighbor in result["neighbors"]:
        rels = kg.get_relationship_context(name, neighbor["name"])
        for r in rels:
            relationships.append({
                "name": neighbor["name"],
                **r,
            })
    result["relationships"] = relationships

    return result


def path_to_d3(kg: KnowledgeGraph, path: list[dict]) -> dict:
    """将 find_connection_path 结果转换为 D3 格式"""
    if not path:
        return {"nodes": [], "edges": [], "length": 0}

    nodes = []
    edges = []

    for step in path:
        node_id = step["id"]
        data = dict(kg.graph.nodes[node_id])
        node = {
            "id": node_id,
            "type": step.get("type", "unknown"),
            "radius": _node_radius(data),
        }
        if step.get("type") == "celebrity":
            node["name"] = data.get("name", "")
        else:
            node["title"] = data.get("title", "")

        nodes.append(node)

    # 查找相邻节点间的边
    for i in range(len(path) - 1):
        u = path[i]["id"]
        v = path[i + 1]["id"]
        # 查找边
        for _, vv, _, edata in kg.graph.edges(nbunch=[u], data=True, keys=True):
            if vv == v and edata.get("edge_type") in ("relationship", "involved_in"):
                edges.append({
                    "source": u,
                    "target": v,
                    "edge_type": edata.get("edge_type", ""),
                    "relation_type": edata.get("relation_type", ""),
                    "role": edata.get("role", ""),
                })
                break
        else:
            # 反方向查找
            for _, uu, _, edata in kg.graph.edges(nbunch=[v], data=True, keys=True):
                if uu == u and edata.get("edge_type") in ("relationship", "involved_in"):
                    edges.append({
                        "source": v,
                        "target": u,
                        "edge_type": edata.get("edge_type", ""),
                        "relation_type": edata.get("relation_type", ""),
                        "role": edata.get("role", ""),
                    })
                    break

    return {"nodes": nodes, "edges": edges, "length": len(path) - 1}
