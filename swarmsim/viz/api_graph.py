# -*- coding: utf-8 -*-
"""
Graph API - 知识图谱 REST API

提供图谱数据、查询、路径查找等端点。
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from swarmsim.graph import KnowledgeGraph
from swarmsim.viz.serializer import graph_to_d3, path_to_d3, person_detail

router = APIRouter(tags=["graph"])


def _kg(request: Request) -> KnowledgeGraph:
    """从 app.state 获取知识图谱"""
    return request.app.state.kg


@router.get("/stats")
def get_stats(request: Request):
    """图谱统计信息"""
    return _kg(request).get_stats()


@router.get("/data")
def get_graph_data(
    request: Request,
    filter: str = Query("celebrity", description="celebrity | all"),
    name: str | None = Query(None, description="邻域查询的人物名"),
    depth: int = Query(2, ge=1, le=3, description="BFS 深度"),
):
    """
    获取图谱数据（D3 node-link 格式）。

    - filter=celebrity: 仅名人和关系边
    - filter=all: 全部节点和边
    - name=某人: 该人的邻域子图
    """
    kg = _kg(request)

    if name and name in kg.celebrity_names:
        return graph_to_d3(kg, filter_type="all", name=name, depth=depth)

    return graph_to_d3(kg, filter_type=filter)


@router.get("/person/{name}")
def get_person(request: Request, name: str):
    """获取名人详情：属性、关系、事件"""
    kg = _kg(request)

    # 模糊匹配
    if name not in kg.celebrity_names:
        candidates = [n for n in kg.celebrity_names if name in n]
        if candidates:
            name = candidates[0]
        else:
            return {"error": f"未找到 '{name}'", "available": sorted(kg.celebrity_names)}

    detail = person_detail(kg, name)
    if not detail:
        return {"error": f"未找到 '{name}'"}

    # 附加 graph context
    detail["graph_context"] = kg.to_context_string(name, max_chars=500)

    return detail


@router.get("/path")
def get_path(
    request: Request,
    from_name: str = Query(..., alias="from"),
    to_name: str = Query(..., alias="to"),
):
    """查找两人之间的最短路径"""
    kg = _kg(request)
    path = kg.find_connection_path(from_name, to_name)
    return path_to_d3(kg, path)


@router.get("/impact")
def get_impact(
    request: Request,
    name: str = Query(...),
    event: str = Query(...),
):
    """评估事件对某人的影响"""
    kg = _kg(request)
    return kg.get_event_impact(event, name)


@router.get("/celebrities")
def get_celebrities(request: Request):
    """获取所有名人列表"""
    kg = _kg(request)
    return {"names": sorted(kg.celebrity_names)}
