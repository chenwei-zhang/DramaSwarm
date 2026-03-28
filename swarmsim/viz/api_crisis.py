# -*- coding: utf-8 -*-
"""
Crisis API - 危机仿真 REST API

提供场景列表、仿真控制、干预注入、结果分析等端点。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from swarmsim.crisis.models import InterventionCondition

router = APIRouter(tags=["crisis"])


# ── Request Models ──

class CrisisStartRequest(BaseModel):
    scenario_title: str
    use_llm: bool = False
    total_days: int = 30
    interventions: list[dict] | None = None


class CrisisStepRequest(BaseModel):
    pass


class CrisisRunRequest(BaseModel):
    days: int | None = None


class CrisisInterveneRequest(BaseModel):
    day: int | None = None
    person: str | None = None
    action: str | None = None
    external_event: str | None = None
    description: str = ""


class CrisisResetRequest(BaseModel):
    pass


# ── Helpers ──

def _get_crisis_engine(request: Request):
    """获取危机场景引擎（从 app.state）"""
    engine = getattr(request.app.state, "crisis_engine", None)
    if engine is None:
        from swarmsim.crisis.scenario_engine import CrisisScenarioEngine
        kg = request.app.state.kg
        engine = CrisisScenarioEngine(kg)
        request.app.state.crisis_engine = engine
    return engine


def _get_simulation(request: Request):
    """获取当前仿真实例"""
    return getattr(request.app.state, "crisis_simulation", None)


# ── Endpoints ──

@router.get("/scenarios")
async def list_scenarios(request: Request):
    """列出所有可用危机场景"""
    engine = _get_crisis_engine(request)
    return {"scenarios": engine.list_scenarios()}


@router.get("/scenario/{title:path}")
async def get_scenario(title: str, request: Request):
    """获取单个场景详情"""
    engine = _get_crisis_engine(request)
    scenario = engine.available_scenarios.get(title)
    if not scenario:
        return {"error": f"未找到场景: {title}"}
    return {
        "title": scenario.title,
        "date": scenario.crisis_date,
        "description": scenario.description,
        "importance": scenario.initial_severity,
        "gossip_type": scenario.gossip_type.value,
        "involved_persons": scenario.involved_persons,
        "historical_outcome": scenario.historical_outcome,
        "has_historical": bool(scenario.historical_outcome),
    }


@router.post("/start")
async def start_simulation(body: CrisisStartRequest, request: Request):
    """启动危机仿真"""
    engine = _get_crisis_engine(request)

    # 解析干预条件
    interventions = None
    if body.interventions:
        interventions = []
        for iv in body.interventions:
            interventions.append(InterventionCondition(
                day=iv.get("day"),
                person=iv.get("person"),
                action=iv.get("action"),
                external_event=iv.get("external_event"),
                description=iv.get("description", ""),
            ))

    try:
        sim = engine.create_simulation(
            scenario_title=body.scenario_title,
            use_llm=body.use_llm,
            total_days=body.total_days,
            interventions=interventions,
        )
        request.app.state.crisis_simulation = sim
        return {
            "status": "started",
            "scenario": body.scenario_title,
            "total_days": body.total_days,
            "initial_state": sim.get_state().to_dict(),
        }
    except ValueError as e:
        return {"error": str(e)}


@router.post("/step")
async def step_simulation(request: Request):
    """推进一天"""
    sim = _get_simulation(request)
    if not sim:
        return {"error": "未启动仿真，请先 POST /api/crisis/start"}
    if sim.is_finished():
        return {"error": "仿真已结束", "state": sim.get_state().to_dict()}

    state = await sim.step()
    return {"status": "ok", "state": state.to_dict()}


@router.post("/run")
async def run_simulation(body: CrisisRunRequest, request: Request):
    """运行仿真到底"""
    sim = _get_simulation(request)
    if not sim:
        return {"error": "未启动仿真，请先 POST /api/crisis/start"}

    history = await sim.run(days=body.days)
    return {
        "status": "completed" if sim.is_finished() else "running",
        "total_days": len(history),
        "history": [s.to_dict() for s in history],
        "final_state": sim.get_state().to_dict(),
    }


@router.post("/intervene")
async def add_intervention(body: CrisisInterveneRequest, request: Request):
    """添加干预条件"""
    sim = _get_simulation(request)
    if not sim:
        return {"error": "未启动仿真"}

    cond = InterventionCondition(
        day=body.day,
        person=body.person,
        action=body.action,
        external_event=body.external_event,
        description=body.description,
    )
    sim.intervention_system.add_intervention(cond)
    return {
        "status": "added",
        "pending": sim.intervention_system.get_pending_descriptions(),
    }


@router.get("/state")
async def get_state(request: Request):
    """获取当前状态"""
    sim = _get_simulation(request)
    if not sim:
        return {"error": "未启动仿真"}
    return {
        "state": sim.get_state().to_dict(),
        "is_finished": sim.is_finished(),
    }


@router.get("/history")
async def get_history(request: Request):
    """获取完整历史"""
    sim = _get_simulation(request)
    if not sim:
        return {"error": "未启动仿真"}
    return {"history": sim.get_history(), "total_days": len(sim.state_history)}


@router.get("/outcome")
async def get_outcome(request: Request):
    """获取结果分析"""
    sim = _get_simulation(request)
    if not sim:
        return {"error": "未启动仿真"}
    if not sim.state_history:
        return {"error": "仿真尚未运行"}

    from swarmsim.crisis.outcome_analyzer import OutcomeAnalyzer
    analyzer = OutcomeAnalyzer()
    report = analyzer.analyze(sim.state_history, sim.scenario)
    return report.to_dict()


@router.post("/reset")
async def reset_simulation(request: Request):
    """重置仿真"""
    sim = _get_simulation(request)
    if sim:
        sim.reset()
        request.app.state.crisis_simulation = None
    return {"status": "reset"}
