# -*- coding: utf-8 -*-
"""
时序知识图谱 - Temporal GraphRAG

在 KnowledgeGraph 基础上增加时间索引，支持按日期查询事件轨迹。
"""

from __future__ import annotations

import bisect
from datetime import datetime
from typing import Any

from swarmsim.graph.knowledge_graph import KnowledgeGraph


class TemporalKnowledgeGraph(KnowledgeGraph):
    """带时间索引的知识图谱"""

    def __init__(self):
        super().__init__()
        # (date_str, node_id) 排序列表，用于二分查找
        self._timeline_index: list[tuple[str, str]] = []
        # person_name → [event_dict] 时间线
        self._person_timelines: dict[str, list[dict]] = {}

    # ── 重写数据加载 ──

    def _add_gossip_node(self, gossip: dict) -> None:
        """添加八卦事件节点（含日期索引）"""
        super()._add_gossip_node(gossip)

        title = gossip.get("title", "")
        date_str = gossip.get("date", "")
        if title and date_str:
            node_id = f"gossip:{title}"
            entry = (date_str, node_id)
            bisect.insort(self._timeline_index, entry)

            # 更新人物时间线
            for person in gossip.get("involved_celebrities", []):
                if person not in self._person_timelines:
                    self._person_timelines[person] = []
                event_data = {
                    "node_id": node_id,
                    "title": title,
                    "date": date_str,
                    "type": "gossip",
                    "importance": float(gossip.get("importance", 0.5)),
                    "gossip_type": gossip.get("gossip_type", "other"),
                    "sentiment": gossip.get("sentiment", "neutral"),
                    "content": gossip.get("content", ""),
                }
                self._person_timelines[person].append(event_data)

    def _add_news_event(self, person_name: str, article: dict) -> None:
        """添加新闻事件（含日期索引）"""
        super()._add_news_event(person_name, article)

        date_str = article.get("publish_date", "")
        title = article.get("title", "")
        if date_str and title:
            node_id = f"news:{person_name}:{title[:30]}"
            entry = (date_str, node_id)
            bisect.insort(self._timeline_index, entry)

            if person_name not in self._person_timelines:
                self._person_timelines[person_name] = []
            event_data = {
                "node_id": node_id,
                "title": title,
                "date": date_str,
                "type": "news",
                "source": article.get("source", ""),
                "sentiment": article.get("sentiment", "neutral"),
            }
            self._person_timelines[person_name].append(event_data)

    # ── 时序查询 ──

    def get_events_in_range(self, start_date: str, end_date: str) -> list[dict]:
        """查询日期范围内的所有事件"""
        results = []
        lo = bisect.bisect_left(self._timeline_index, (start_date, ""))
        hi = bisect.bisect_right(self._timeline_index, (end_date + "\xff", ""))

        for date_str, node_id in self._timeline_index[lo:hi]:
            if start_date <= date_str <= end_date:
                data = dict(self._graph.nodes[node_id])
                data["date"] = date_str
                results.append(data)

        return results

    def get_events_on_date(self, date_str: str) -> list[dict]:
        """查询某天的事件"""
        return self.get_events_in_range(date_str, date_str)

    def get_person_timeline(self, name: str) -> list[dict]:
        """获取某人的完整事件时间线"""
        entries = self._person_timelines.get(name, [])
        return sorted(entries, key=lambda e: e.get("date", ""))

    def get_person_events_in_range(
        self, name: str, start_date: str, end_date: str
    ) -> list[dict]:
        """获取某人在日期范围内的事件"""
        timeline = self.get_person_timeline(name)
        return [
            e for e in timeline
            if start_date <= e.get("date", "") <= end_date
        ]

    def get_all_timelines(self) -> dict[str, list[dict]]:
        """获取所有人物的时间线"""
        return {name: self.get_person_timeline(name) for name in self._person_timelines}

    # ── 场景数据提取 ──

    def get_crisis_scenario_data(self, event_title: str) -> dict | None:
        """从图谱提取完整危机场景数据"""
        node_id = f"gossip:{event_title}"
        if not self._graph.has_node(node_id):
            return None

        node_data = dict(self._graph.nodes[node_id])

        # 找到涉及的人
        involved_persons = []
        for pred in self._graph.predecessors(node_id):
            pred_data = self._graph.nodes[pred]
            if pred_data.get("node_type") == "celebrity":
                involved_persons.append(pred_data.get("name", ""))

        # 获取他们的关系
        relationships = []
        seen_pairs = set()
        for person in involved_persons:
            person_id = f"celebrity:{person}"
            for succ in self._graph.successors(person_id):
                succ_data = self._graph.nodes[succ]
                if succ_data.get("node_type") != "celebrity":
                    continue
                other_name = succ_data.get("name", "")
                pair = tuple(sorted([person, other_name]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                for _, _, _, edge_data in self._graph.edges(
                    nbunch=[person_id], data=True, keys=True
                ):
                    if _ == succ and edge_data.get("edge_type") == "relationship":
                        relationships.append({
                            "person_a": person,
                            "person_b": other_name,
                            "relation_type": edge_data.get("relation_type", ""),
                            "strength": edge_data.get("strength", 0.5),
                            "is_current": edge_data.get("is_current", True),
                            "description": edge_data.get("description", ""),
                        })
                        break

        # 获取每个人的信息
        person_profiles = {}
        for person in involved_persons:
            person_id = f"celebrity:{person}"
            if self._graph.has_node(person_id):
                person_profiles[person] = dict(self._graph.nodes[person_id])

        return {
            "title": node_data.get("title", event_title),
            "date": node_data.get("date", ""),
            "importance": node_data.get("importance", 0.5),
            "gossip_type": node_data.get("gossip_type", "other"),
            "sentiment": node_data.get("sentiment", "neutral"),
            "content": node_data.get("content", ""),
            "involved_persons": involved_persons,
            "relationships": relationships,
            "person_profiles": person_profiles,
        }

    def list_crisis_scenarios(self, min_importance: float = 0.6) -> list[dict]:
        """列出所有可用的危机场景"""
        scenarios = []
        for node_id, data in self._graph.nodes(data=True):
            if data.get("node_type") != "gossip":
                continue
            if data.get("importance", 0) < min_importance:
                continue

            involved = []
            for pred in self._graph.predecessors(node_id):
                pred_data = self._graph.nodes[pred]
                if pred_data.get("node_type") == "celebrity":
                    involved.append(pred_data.get("name", ""))

            scenarios.append({
                "title": data.get("title", ""),
                "date": data.get("date", ""),
                "importance": data.get("importance", 0),
                "gossip_type": data.get("gossip_type", "other"),
                "involved_persons": involved,
            })

        scenarios.sort(key=lambda x: x["importance"], reverse=True)
        return scenarios

    # ── 重置 ──

    def reset(self) -> None:
        super().reset()
        self._timeline_index.clear()
        self._person_timelines.clear()
