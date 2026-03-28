# -*- coding: utf-8 -*-
"""
危机仿真引擎 - 多智能体公关危机模拟

基于时序 GraphRAG 的危机场景仿真，支持 what-if 干预和结果对比分析。
"""

from swarmsim.crisis.models import (
    CrisisPhase, PRAction, GossipType,
    CrisisScenario, CrisisAction, CrisisState,
    InterventionCondition, CrisisOutcomeReport,
    TrendingTopic, MediaHeadline, BrandStatus,
)
from swarmsim.crisis.timeline import CrisisTimeline
from swarmsim.crisis.action_space import CrisisActionSpace
from swarmsim.crisis.persona_agent import CelebrityPersonaAgent
from swarmsim.crisis.intervention import InterventionSystem
from swarmsim.crisis.vacuum_detector import InformationVacuumDetector
from swarmsim.crisis.scenario_engine import CrisisScenarioEngine, CrisisSimulation
from swarmsim.crisis.outcome_analyzer import OutcomeAnalyzer
