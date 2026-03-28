# -*- coding: utf-8 -*-
"""
DramaSwarm 可视化服务器

FastAPI 应用，提供图谱和仿真 API，并托管前端静态页面。
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from swarmsim.graph import KnowledgeGraph
from swarmsim.viz.api_graph import router as graph_router
from swarmsim.viz.api_simulation import router as sim_router


def _load_knowledge_graph() -> KnowledgeGraph:
    """加载知识图谱"""
    kg = KnowledgeGraph()

    # 尝试从 celebrity_scraper/data 加载
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "celebrity_scraper", "data"
    )

    if os.path.exists(data_dir):
        stats = kg.load_from_json_dir(data_dir)
        if stats["celebrities"] > 0:
            print(f"知识图谱已加载: {stats['celebrities']}位明星, "
                  f"{stats['relationships']}条关系, "
                  f"{stats['gossips']}个事件, "
                  f"{stats['news']}条新闻")
            return kg

    # 降级到 mock 数据
    print("未找到爬虫数据，使用 mock 数据...")
    mock_names = ["肖战", "王一博", "杨幂", "赵丽颖", "迪丽热巴",
                  "李小璐", "贾乃亮", "PG One", "唐嫣", "罗晋"]
    stats = kg.load_from_mock_data(mock_names)
    if stats["celebrities"] > 0:
        print(f"Mock 知识图谱已加载: {stats['celebrities']}位明星, "
              f"{stats['relationships']}条关系, "
              f"{stats['gossips']}个事件, "
              f"{stats['news']}条新闻")
    else:
        for name in mock_names:
            kg._add_celebrity_node(name, {})
        print(f"基础图谱已加载: {kg.node_count}位明星")

    return kg


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时加载图谱
    app.state.kg = _load_knowledge_graph()
    app.state.environment = None
    app.state.observer = None
    app.state.event_loop = None
    yield


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="DramaSwarm GraphRAG",
        description="多智能体群体仿真可视化",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 路由
    app.include_router(graph_router, prefix="/api/graph")
    app.include_router(sim_router, prefix="/api/sim")

    # 静态文件
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 首页
    @app.get("/")
    async def index():
        html_path = static_dir / "index.html"
        if html_path.exists():
            return FileResponse(str(html_path))
        return {"message": "DramaSwarm GraphRAG API", "docs": "/docs"}

    return app


app = create_app()
