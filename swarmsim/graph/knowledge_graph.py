# -*- coding: utf-8 -*-
"""
知识图谱核心引擎

基于 networkx 的 MultiDiGraph，支持名人关系、八卦事件、合作作品的图结构建模。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import networkx as nx


class KnowledgeGraph:
    """知识图谱引擎"""

    def __init__(self):
        self._graph = nx.MultiDiGraph()
        self._names: set[str] = set()  # 快速查找图中人名

    # ── 属性 ──

    @property
    def graph(self) -> nx.MultiDiGraph:
        return self._graph

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    @property
    def celebrity_names(self) -> set[str]:
        return self._names.copy()

    # ── 数据加载 ──

    def load_from_json_dir(self, data_dir: str) -> dict:
        """
        从 celebrity_scraper/data/*.json 加载数据。

        Returns:
            加载统计 {celebrities, gossips, relationships, ...}
        """
        stats = {"celebrities": 0, "gossips": 0, "relationships": 0,
                 "news": 0, "social_posts": 0}

        data_path = Path(data_dir)
        if not data_path.exists():
            return stats

        # Pass 1: 加载每个名人文件
        for json_file in sorted(data_path.glob("*.json")):
            if json_file.name == "summary.json":
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            self._load_celebrity_data(data, stats)

        # Pass 2: 跨文件去重 GossipEvent（同标题合并）
        self._deduplicate_gossip_nodes()

        return stats

    def load_from_mock_data(self, names: list[str]) -> dict:
        """从 mock_data 加载（测试用）"""
        stats = {"celebrities": 0, "gossips": 0, "relationships": 0,
                 "news": 0, "social_posts": 0}

        try:
            from celebrity_scraper.mock_data import (
                MOCK_CELEBRITY_PROFILES, GOSSIP_DATABASE, RELATIONSHIP_MAP,
            )
        except ImportError:
            return stats

        profiles = MOCK_CELEBRITY_PROFILES

        for name in names:
            profile = profiles.get(name)
            if not profile:
                continue

            # 创建 Celebrity 节点
            self._add_celebrity_node(name, {
                "occupation": profile.get("occupation", []),
                "company": profile.get("company", ""),
                "biography": profile.get("biography", ""),
                "famous_works": profile.get("famous_works", []),
                "weibo_followers": profile.get("weibo_followers", 0),
            })
            stats["celebrities"] += 1

        # 加载关系
        for (a, b), rel_data in RELATIONSHIP_MAP.items():
            if a in self._names and b in self._names:
                self._add_relationship_edge(a, b, rel_data)
                stats["relationships"] += 1

        # 加载八卦
        for gossip in GOSSIP_DATABASE:
            involved = gossip.get("involved_celebrities", [])
            if any(n in self._names for n in involved):
                self._add_gossip_node(gossip)
                stats["gossips"] += 1

        return stats

    def _load_celebrity_data(self, data: dict, stats: dict) -> None:
        """加载单个名人 JSON 数据"""
        celebrity = data.get("celebrity", {})
        name = celebrity.get("name", "")
        if not name:
            return

        # 创建 Celebrity 节点
        self._add_celebrity_node(name, {
            "english_name": celebrity.get("english_name", ""),
            "occupation": celebrity.get("occupation", []),
            "company": celebrity.get("company", ""),
            "biography": celebrity.get("biography", ""),
            "famous_works": celebrity.get("famous_works", []),
            "weibo_followers": celebrity.get("weibo_followers", 0),
        })
        stats["celebrities"] += 1

        # 创建 relationship 边
        for rel in data.get("relationships", []):
            other = rel.get("person_b", "") or rel.get("person_a", "")
            if other == name:
                other = rel.get("person_a", "")
            if other:
                self._add_relationship_edge(name, other, rel)
                stats["relationships"] += 1

        # 创建 GossipEvent 节点
        for gossip in data.get("gossips", []):
            self._add_gossip_node(gossip)
            stats["gossips"] += 1

        # 新闻作为轻量事件
        for article in data.get("news_articles", []):
            self._add_news_event(name, article)
            stats["news"] += 1

    def _add_celebrity_node(self, name: str, attrs: dict) -> None:
        """添加名人节点"""
        self._names.add(name)
        node_id = f"celebrity:{name}"
        if not self._graph.has_node(node_id):
            self._graph.add_node(node_id, node_type="celebrity", name=name, **attrs)
        else:
            # 合并属性
            existing = self._graph.nodes[node_id]
            for k, v in attrs.items():
                if k not in existing or not existing[k]:
                    existing[k] = v

    def _add_relationship_edge(self, person_a: str, person_b: str, rel_data: dict) -> None:
        """添加关系边（双向）"""
        node_a = f"celebrity:{person_a}"
        node_b = f"celebrity:{person_b}"

        # 确保两端节点存在
        for name, nid in [(person_a, node_a), (person_b, node_b)]:
            if not self._graph.has_node(nid):
                self._add_celebrity_node(name, {})

        edge_data = {
            "relation_type": rel_data.get("relation_type", "合作"),
            "strength": float(rel_data.get("strength", 0.5)),
            "confidence": float(rel_data.get("confidence", 0.5)),
            "is_current": rel_data.get("is_current", True),
            "description": rel_data.get("description", ""),
        }

        # 双向添加
        self._graph.add_edge(node_a, node_b, edge_type="relationship", **edge_data)
        self._graph.add_edge(node_b, node_a, edge_type="relationship", **edge_data)

    def _add_gossip_node(self, gossip: dict) -> None:
        """添加八卦事件节点和 involved_in 边"""
        title = gossip.get("title", "")
        if not title:
            return

        node_id = f"gossip:{title}"
        involved = gossip.get("involved_celebrities", [])

        if not self._graph.has_node(node_id):
            self._graph.add_node(node_id,
                node_type="gossip",
                title=title,
                gossip_type=gossip.get("gossip_type", "other"),
                importance=float(gossip.get("importance", 0.5)),
                sentiment=gossip.get("sentiment", "neutral"),
                content=gossip.get("content", ""),
            )

        for person_name in involved:
            celeb_id = f"celebrity:{person_name}"
            if self._graph.has_node(celeb_id):
                self._graph.add_edge(celeb_id, node_id,
                    edge_type="involved_in",
                    role="primary" if person_name in title else "mentioned")

    def _add_news_event(self, person_name: str, article: dict) -> None:
        """添加新闻事件（轻量节点）"""
        title = article.get("title", "")
        if not title:
            return

        node_id = f"news:{person_name}:{title[:30]}"

        if not self._graph.has_node(node_id):
            self._graph.add_node(node_id,
                node_type="news",
                title=title,
                source=article.get("source", ""),
                date=article.get("publish_date", ""),
                sentiment=article.get("sentiment", "neutral"),
            )

            celeb_id = f"celebrity:{person_name}"
            if self._graph.has_node(celeb_id):
                self._graph.add_edge(celeb_id, node_id,
                    edge_type="involved_in", role="subject")

    def _deduplicate_gossip_nodes(self) -> None:
        """去重同标题的八卦节点（合并边）"""
        gossip_nodes = [
            (n, d) for n, d in self._graph.nodes(data=True)
            if d.get("node_type") == "gossip"
        ]
        seen_titles: dict[str, str] = {}
        for node_id, data in gossip_nodes:
            title = data.get("title", "")
            if title in seen_titles:
                # 合并边到已存在节点
                existing_id = seen_titles[title]
                for pred in list(self._graph.predecessors(node_id)):
                    for key in list(self._graph.pred[node_id][pred].keys()):
                        edge_data = dict(self._graph.edges[pred, node_id, key])
                        self._graph.add_edge(pred, existing_id, **edge_data)
                self._graph.remove_node(node_id)
            else:
                seen_titles[title] = node_id

    # ── 仿真中动态变更 ──

    def add_simulation_event(self, from_name: str, to_name: str,
                              action_type: str, content: str,
                              turn: int, severity: float) -> None:
        """在仿真中记录动态事件边"""
        node_a = f"celebrity:{from_name}"
        node_b = f"celebrity:{to_name}"
        if not (self._graph.has_node(node_a) and self._graph.has_node(node_b)):
            return

        self._graph.add_edge(node_a, node_b,
            edge_type="simulation_event",
            action_type=action_type,
            content=content[:100],
            turn=turn,
            severity=severity,
            weight=max(0.1, severity),
        )

    def update_relationship_strength(self, name_a: str, name_b: str,
                                      delta: float) -> None:
        """更新关系强度"""
        node_a = f"celebrity:{name_a}"
        node_b = f"celebrity:{name_b}"

        for u, v, key, data in self._graph.edges(nbunch=[node_a], data=True, keys=True):
            if v == node_b and data.get("edge_type") == "relationship":
                data["strength"] = max(0.0, min(1.0, data["strength"] + delta))

        for u, v, key, data in self._graph.edges(nbunch=[node_b], data=True, keys=True):
            if v == node_a and data.get("edge_type") == "relationship":
                data["strength"] = max(0.0, min(1.0, data["strength"] + delta))

    def decay_simulation_edges(self, rate: float = 0.3) -> None:
        """衰减仿真事件边的权重，低于阈值删除"""
        to_remove = []
        for u, v, key, data in self._graph.edges(data=True, keys=True):
            if data.get("edge_type") == "simulation_event":
                data["weight"] = data.get("weight", 0.5) * (1 - rate)
                if data["weight"] < 0.05:
                    to_remove.append((u, v, key))

        for u, v, key in to_remove:
            self._graph.remove_edge(u, v, key)

    # ── 查询方法 ──

    def get_relationship_context(self, name_a: str, name_b: str) -> list[dict]:
        """查询两人之间的所有关系边"""
        node_a = f"celebrity:{name_a}"
        node_b = f"celebrity:{name_b}"
        results = []

        for u, v, key, data in self._graph.edges(nbunch=[node_a], data=True, keys=True):
            if v == node_b and data.get("edge_type") == "relationship":
                results.append(dict(data))

        return results

    def get_social_neighborhood(self, name: str, max_depth: int = 2) -> list[dict]:
        """BFS 获取社交邻域"""
        node_id = f"celebrity:{name}"
        if not self._graph.has_node(node_id):
            return []

        neighbors = []
        visited = {node_id}
        current_level = [node_id]

        for depth in range(1, max_depth + 1):
            next_level = []
            for n in current_level:
                for successor in self._graph.successors(n):
                    if successor in visited:
                        continue
                    visited.add(successor)
                    next_level.append(successor)

                    node_data = self._graph.nodes[successor]
                    if node_data.get("node_type") == "celebrity":
                        # 查找关系类型
                        rels = []
                        for u, v, key, ed in self._graph.edges(nbunch=[n], data=True, keys=True):
                            if v == successor and ed.get("edge_type") == "relationship":
                                rels.append(ed.get("relation_type", "未知"))
                        neighbors.append({
                            "name": node_data.get("name", ""),
                            "depth": depth,
                            "relation_types": rels,
                        })

            current_level = next_level

        return neighbors

    def find_connection_path(self, name_a: str, name_b: str) -> list[dict]:
        """查找两人之间的最短路径"""
        node_a = f"celebrity:{name_a}"
        node_b = f"celebrity:{name_b}"

        if not (self._graph.has_node(node_a) and self._graph.has_node(node_b)):
            return []

        # 构建无向简化图（仅 relationship + involved_in 边）
        simple = nx.Graph()
        for u, v, key, data in self._graph.edges(data=True, keys=True):
            if data.get("edge_type") in ("relationship", "involved_in"):
                simple.add_edge(u, v)

        try:
            path = nx.shortest_path(simple, node_a, node_b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

        result = []
        for node_id in path:
            data = self._graph.nodes[node_id]
            result.append({
                "id": node_id,
                "type": data.get("node_type", ""),
                "name": data.get("name", ""),
                "title": data.get("title", ""),
            })
        return result

    def get_related_events(self, name: str, depth: int = 1) -> list[dict]:
        """获取关联事件"""
        node_id = f"celebrity:{name}"
        if not self._graph.has_node(node_id):
            return []

        events = []
        for successor in self._graph.successors(node_id):
            node_data = self._graph.nodes[successor]
            if node_data.get("node_type") in ("gossip", "news"):
                events.append({
                    "title": node_data.get("title", ""),
                    "type": node_data.get("node_type", ""),
                    "importance": node_data.get("importance", 0.5),
                    "sentiment": node_data.get("sentiment", "neutral"),
                })

        # 按重要性排序
        events.sort(key=lambda x: x["importance"], reverse=True)
        return events[:10]

    def get_event_impact(self, event_text: str, agent_name: str) -> dict:
        """评估事件对 agent 的影响"""
        mentioned = self.find_mentioned_names(event_text)

        if not mentioned:
            return {"severity_delta": 0.0, "affected_relationships": []}

        affected = []
        total_delta = 0.0

        for other_name in mentioned:
            if other_name == agent_name:
                continue
            rels = self.get_relationship_context(agent_name, other_name)
            for rel in rels:
                rel_type = rel.get("relation_type", "合作")
                strength = rel.get("strength", 0.5)

                # 亲密关系的事件影响更大
                impact_map = {
                    "配偶": 0.3, "前任": 0.25, "绯闻": 0.2,
                    "搭档": 0.15, "合作": 0.1, "好友": 0.1,
                    "对手": 0.15, "竞争对手": 0.15,
                }
                delta = impact_map.get(rel_type, 0.05) * strength
                total_delta += delta
                affected.append({
                    "name": other_name,
                    "relation_type": rel_type,
                    "impact": delta,
                })

        return {
            "severity_delta": min(0.3, total_delta),
            "affected_relationships": affected,
        }

    def find_mentioned_names(self, text: str) -> list[str]:
        """从文本中识别图中的名人名"""
        found = []
        for name in self._names:
            if name in text:
                found.append(name)
        return found

    # ── 上下文生成 ──

    def to_context_string(self, agent_name: str, max_chars: int = 300) -> str:
        """为 agent 生成中文图上下文文本"""
        if agent_name not in self._names:
            return ""

        parts = []

        # 直接关系
        neighbors = self.get_social_neighborhood(agent_name, max_depth=1)
        if neighbors:
            rel_strs = []
            for n in neighbors[:8]:
                types = "、".join(n["relation_types"]) if n["relation_types"] else "关联"
                rel_strs.append(f"{n['name']}({types})")
            parts.append(f"【直接关系】{', '.join(rel_strs)}")

        # 关联事件
        events = self.get_related_events(agent_name)
        if events:
            event_strs = [f"{e['title']}" for e in events[:3]]
            parts.append(f"【关联事件】{'; '.join(event_strs)}")

        # 二度连接摘要
        neighbors_2 = self.get_social_neighborhood(agent_name, max_depth=2)
        second_degree = [n for n in neighbors_2 if n["depth"] == 2]
        if second_degree:
            names_2 = [n["name"] for n in second_degree[:5]]
            parts.append(f"【二度连接】{', '.join(names_2)}等{len(second_degree)}人")

        result = "\n".join(parts)

        if len(result) > max_chars:
            result = result[:max_chars - 3] + "..."

        return result

    # ── 导出 ──

    def get_stats(self) -> dict:
        """获取图统计信息"""
        node_types = {}
        for _, data in self._graph.nodes(data=True):
            t = data.get("node_type", "unknown")
            node_types[t] = node_types.get(t, 0) + 1

        edge_types = {}
        for _, _, _, data in self._graph.edges(data=True, keys=True):
            t = data.get("edge_type", "unknown")
            edge_types[t] = edge_types.get(t, 0) + 1

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "node_types": node_types,
            "edge_types": edge_types,
            "celebrities": sorted(self._names),
        }

    def reset(self) -> None:
        """重置图谱"""
        self._graph.clear()
        self._names.clear()
