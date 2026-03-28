# -*- coding: utf-8 -*-
"""测试危机仿真引擎"""

import pytest
import asyncio

from swarmsim.crisis.models import (
    CrisisPhase, PRAction, GossipType,
    CrisisAction, CrisisState, InterventionCondition,
)
from swarmsim.crisis.timeline import CrisisTimeline
from swarmsim.crisis.action_space import CrisisActionSpace, ACTION_EFFECTS, PHASE_MODIFIERS
from swarmsim.crisis.vacuum_detector import InformationVacuumDetector
from swarmsim.crisis.intervention import InterventionSystem


class TestCrisisTimeline:

    def test_initial_phase(self):
        tl = CrisisTimeline("2024-01-01")
        assert tl.current_day == 0
        assert tl.get_phase() == CrisisPhase.BREAKOUT

    def test_advance_day(self):
        tl = CrisisTimeline("2024-01-01")
        phase = tl.advance_day()
        assert tl.current_day == 1
        assert phase == CrisisPhase.BREAKOUT

    def test_phase_escalation(self):
        tl = CrisisTimeline("2024-01-01")
        tl.current_day = 2
        assert tl.get_phase() == CrisisPhase.ESCALATION

    def test_phase_peak(self):
        tl = CrisisTimeline("2024-01-01")
        tl.current_day = 5
        assert tl.get_phase() == CrisisPhase.PEAK

    def test_phase_mitigation(self):
        tl = CrisisTimeline("2024-01-01")
        tl.current_day = 10
        assert tl.get_phase() == CrisisPhase.MITIGATION

    def test_phase_resolution(self):
        tl = CrisisTimeline("2024-01-01")
        tl.current_day = 18
        assert tl.get_phase() == CrisisPhase.RESOLUTION

    def test_phase_aftermath(self):
        tl = CrisisTimeline("2024-01-01")
        tl.current_day = 25
        assert tl.get_phase() == CrisisPhase.AFTERMATH

    def test_current_date(self):
        tl = CrisisTimeline("2024-01-01")
        tl.current_day = 3
        assert tl.current_date() == "2024-01-04"

    def test_is_finished(self):
        tl = CrisisTimeline("2024-01-01", total_days=5)
        tl.current_day = 5
        assert tl.is_finished()

    def test_day_label(self):
        tl = CrisisTimeline("2024-01-01")
        label = tl.day_label()
        assert "第0天" in label

    def test_to_dict(self):
        tl = CrisisTimeline("2024-01-01", total_days=30)
        d = tl.to_dict()
        assert d["start_date"] == "2024-01-01"
        assert d["total_days"] == 30
        assert "phase" in d


class TestCrisisActionSpace:

    def test_all_actions_have_effects(self):
        for action in PRAction:
            assert action in ACTION_EFFECTS

    def test_all_phases_have_modifiers(self):
        for phase in CrisisPhase:
            assert phase in PHASE_MODIFIERS
            for action in PRAction:
                assert action in PHASE_MODIFIERS[phase]

    def test_compute_effect(self):
        space = CrisisActionSpace()
        effect = space.compute_effect(PRAction.APOLOGIZE, CrisisPhase.PEAK, 50.0)
        assert "approval_delta" in effect
        assert "heat_delta" in effect
        assert "rumor_multiplier" in effect
        assert "brand_delta" in effect

    def test_apologize_at_peak_is_effective(self):
        space = CrisisActionSpace()
        effect = space.compute_effect(PRAction.APOLOGIZE, CrisisPhase.PEAK, 50.0)
        assert effect["approval_delta"] > 0

    def test_silence_at_peak_is_bad(self):
        space = CrisisActionSpace()
        effect = space.compute_effect(PRAction.SILENCE, CrisisPhase.PEAK, 50.0)
        # 沉默在高峰期 heat 应该增加
        assert effect["heat_delta"] > 0

    def test_personality_modifier(self):
        space = CrisisActionSpace()
        # 神经质高的人反击更冲动
        normal = space.compute_effect(PRAction.COUNTERATTACK, CrisisPhase.PEAK, 50.0, {})
        neurotic = space.compute_effect(
            PRAction.COUNTERATTACK, CrisisPhase.PEAK, 50.0,
            {"neuroticism": 0.9}
        )
        assert neurotic["modifier"] >= normal["modifier"]

    def test_get_available_actions(self):
        space = CrisisActionSpace()
        actions = space.get_available_actions(CrisisPhase.PEAK)
        assert len(actions) == len(PRAction)
        assert actions[0]["effectiveness"] >= actions[-1]["effectiveness"]


class TestVacuumDetector:

    def test_silence_triggers_rumor(self):
        detector = InformationVacuumDetector()
        # 模拟3天沉默
        for day in range(1, 4):
            rumors = detector.update(
                day=day,
                day_actions=[],
                involved_persons=["李小璐"],
                gossip_type="cheating",
            )
        # 第3天沉默，可能产生谣言
        assert detector.silence_days.get("李小璐", 0) >= 2

    def test_action_resets_silence(self):
        detector = InformationVacuumDetector()
        detector.silence_days["李小璐"] = 5
        action = CrisisAction(actor="李小璐", action=PRAction.APOLOGIZE)
        detector.update(day=1, day_actions=[action], involved_persons=["李小璐"])
        assert detector.silence_days["李小璐"] == 0

    def test_rumor_impact(self):
        detector = InformationVacuumDetector()
        rumor = {"severity": 0.7}
        impact = detector.get_rumor_impact(rumor)
        assert impact["approval_delta"] < 0
        assert impact["heat_delta"] > 0

    def test_reset(self):
        detector = InformationVacuumDetector()
        detector.silence_days["test"] = 5
        detector.generated_rumors.append({"test": True})
        detector.reset()
        assert len(detector.silence_days) == 0
        assert len(detector.generated_rumors) == 0


class TestInterventionSystem:

    def test_add_and_check(self):
        system = InterventionSystem()
        cond = InterventionCondition(day=3, description="测试干预")
        system.add_intervention(cond)
        triggered = system.check_interventions(3)
        assert len(triggered) == 1
        assert triggered[0].description == "测试干预"

    def test_wrong_day_not_triggered(self):
        system = InterventionSystem()
        cond = InterventionCondition(day=5, description="第5天干预")
        system.add_intervention(cond)
        triggered = system.check_interventions(3)
        assert len(triggered) == 0
        assert len(system.pending) == 1

    def test_apply_intervention(self):
        system = InterventionSystem()
        cond = InterventionCondition(
            person="李小璐",
            action="silence",
            description="李小璐不上节目",
        )
        effects = system.apply_intervention(cond, None)
        assert effects["description"] == "李小璐不上节目"
        assert "forced_action" in effects

    def test_reset(self):
        system = InterventionSystem()
        system.add_intervention(InterventionCondition(day=1))
        system.check_interventions(1)
        system.reset()
        assert len(system.pending) == 0
        assert len(system.applied) == 0


class TestCrisisPhase:

    def test_labels(self):
        assert CrisisPhase.BREAKOUT.label == "爆发期"
        assert CrisisPhase.ESCALATION.label == "发酵期"
        assert CrisisPhase.PEAK.label == "高峰期"
        assert CrisisPhase.MITIGATION.label == "应对期"
        assert CrisisPhase.RESOLUTION.label == "收尾期"
        assert CrisisPhase.AFTERMATH.label == "余波期"


class TestPRAction:

    def test_labels(self):
        assert PRAction.SILENCE.label == "沉默不回应"
        assert PRAction.APOLOGIZE.label == "公开道歉"
        assert PRAction.COUNTERATTACK.label == "反击否认"
