# -*- coding: utf-8 -*-
"""
Simulation API - 仿真状态 REST API

提供仿真控制、状态查询、历史数据等端点。
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(tags=["simulation"])


class SimStartRequest(BaseModel):
    names: list[str] = ["杨幂", "李小璐", "贾乃亮", "PG One", "唐嫣"]
    turns: int = 15
    use_llm: bool = False


class InjectEventRequest(BaseModel):
    event_type: str = "conflict"
    content: str = ""
    severity: float = 0.5


def _sim_state(request: Request) -> dict:
    """获取当前仿真状态"""
    state = {}
    env = getattr(request.app.state, "environment", None)
    observer = getattr(request.app.state, "observer", None)
    event_loop = getattr(request.app.state, "event_loop", None)

    if env:
        state["environment"] = env.to_dict()
        state["agents"] = [a.to_dict() for a in env.agents.values()]

    if observer:
        state["group_dynamics"] = observer.analyze_group_dynamics()

    if event_loop:
        state["loop_stats"] = event_loop.get_statistics()

    return state


@router.get("/state")
def get_state(request: Request):
    """获取当前仿真完整状态"""
    return _sim_state(request)


@router.get("/history")
def get_history(
    request: Request,
    limit: int = Query(20, ge=1, le=200),
):
    """获取最近的行动历史"""
    event_loop = getattr(request.app.state, "event_loop", None)
    if not event_loop:
        return {"actions": [], "total": 0}

    return {
        "actions": event_loop.get_action_summary(limit),
        "total": len(event_loop.action_history),
    }


@router.get("/snapshots")
def get_snapshots(
    request: Request,
    start: int = Query(0, ge=0),
    end: int = Query(-1),
):
    """获取反应系统时间序列快照"""
    env = getattr(request.app.state, "environment", None)
    if not env or not hasattr(env, "reaction_bus"):
        return {"snapshots": []}

    snapshots = env.reaction_bus.snapshots
    if end < 0:
        end = len(snapshots)

    result = []
    for snap in snapshots[start:end]:
        result.append({
            "turn": getattr(snap, "turn", 0),
            "timestamp": getattr(snap, "timestamp", ""),
        })

    return {"snapshots": result, "total": len(snapshots)}


@router.post("/start")
async def start_simulation(request: Request, config: SimStartRequest):
    """启动仿真（后台运行）"""
    # 如果已在运行，先停止
    event_loop = getattr(request.app.state, "event_loop", None)
    if event_loop and event_loop.is_running:
        event_loop.stop()
        await asyncio.sleep(0.5)

    try:
        from swarmsim.core.environment import VarietyShowEnvironment
        from swarmsim.core.event_loop import SequentialEventLoop, EventLoopConfig
        from swarmsim.core.agent import SimpleAgent, LLMAgent, AgentRole
        from swarmsim.core.observer import Observer
        from swarmsim.graph import KnowledgeGraph

        # 创建环境
        env = VarietyShowEnvironment(
            name="综艺修罗场",
            initial_budget=1000.0,
            task_complexity=0.6,
        )

        # 设置知识图谱
        kg: KnowledgeGraph = request.app.state.kg
        env.knowledge_graph = kg

        # 创建 Agent
        roles = ["leader", "perfectionist", "drama_queen", "slacker", "peacemaker"]
        agents = []
        for i, name in enumerate(config.names):
            role = roles[i % len(roles)]
            if config.use_llm:
                agent = LLMAgent(name=name, role=AgentRole(role))
            else:
                agent = SimpleAgent(name=name, role=AgentRole(role))
            agents.append(agent)

        # 创建事件循环
        loop_config = EventLoopConfig(
            tick_interval=0.5,
            max_turns=config.turns,
            agents_per_turn=len(config.names),
            enable_parallel=False,
        )
        event_loop = SequentialEventLoop(env, loop_config)

        for agent in agents:
            event_loop.add_agent(agent)

        # 创建观察者
        observer = Observer()

        # 设置回调
        def on_action(action):
            observer.observe_action(action.to_dict())

        event_loop.on_action = on_action

        # 存储到 app.state
        request.app.state.environment = env
        request.app.state.observer = observer
        request.app.state.event_loop = event_loop

        # 设置初始任务
        env.set_task("综艺节目八卦讨论", deadline_hours=2)
        env.broadcast(
            "导演组宣布：今天聊八卦！大家对娱乐圈的事怎么看？",
            source="director",
            importance=0.9,
        )

        # 后台运行仿真
        async def _run():
            await event_loop.run(max_turns=config.turns)

        asyncio.create_task(_run())

        return {"status": "started", "names": config.names, "turns": config.turns}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/pause")
def pause_simulation(request: Request):
    """暂停仿真"""
    event_loop = getattr(request.app.state, "event_loop", None)
    if event_loop:
        event_loop.pause()
        return {"status": "paused"}
    return {"status": "no_simulation"}


@router.post("/resume")
def resume_simulation(request: Request):
    """恢复仿真"""
    event_loop = getattr(request.app.state, "event_loop", None)
    if event_loop:
        event_loop.resume()
        return {"status": "resumed"}
    return {"status": "no_simulation"}


@router.post("/stop")
def stop_simulation(request: Request):
    """停止仿真"""
    event_loop = getattr(request.app.state, "event_loop", None)
    if event_loop:
        event_loop.stop()
        return {"status": "stopped"}
    return {"status": "no_simulation"}


@router.post("/inject")
def inject_event(request: Request, event: InjectEventRequest):
    """注入外部事件"""
    env = getattr(request.app.state, "environment", None)
    if not env:
        return {"status": "no_environment"}

    env.add_event(
        event_type=event.event_type,
        description=event.content,
        severity=event.severity,
    )
    env.broadcast(
        event.content,
        source="director",
        importance=event.severity,
    )
    return {"status": "injected"}
