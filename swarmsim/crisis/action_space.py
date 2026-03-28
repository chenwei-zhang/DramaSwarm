# -*- coding: utf-8 -*-
"""
公关动作空间 - 10 种 PR 策略及其效果矩阵

每个动作对 approval/heat/rumor/brand 有不同影响，且受危机阶段修正。
"""

from __future__ import annotations

from swarmsim.crisis.models import CrisisPhase, PRAction


# ── 动作基础效果 ──

ACTION_EFFECTS: dict[PRAction, dict] = {
    PRAction.SILENCE: {
        "approval_delta": 0,
        "heat_delta": 5,
        "rumor_multiplier": 1.3,
        "brand_delta": -0.5,
        "description": "选择沉默，不做任何回应",
    },
    PRAction.APOLOGIZE: {
        "approval_delta": 8,
        "heat_delta": -15,
        "rumor_multiplier": 0.4,
        "brand_delta": 3,
        "description": "公开道歉，承认错误并请求原谅",
    },
    PRAction.STATEMENT: {
        "approval_delta": 3,
        "heat_delta": -5,
        "rumor_multiplier": 0.7,
        "brand_delta": 1,
        "description": "发布官方声明澄清",
    },
    PRAction.GO_ON_SHOW: {
        "approval_delta": 5,
        "heat_delta": -10,
        "rumor_multiplier": 0.3,
        "brand_delta": 2,
        "description": "上节目正面回应",
    },
    PRAction.LAWSUIT: {
        "approval_delta": 2,
        "heat_delta": 5,
        "rumor_multiplier": 0.5,
        "brand_delta": 0,
        "description": "起诉造谣者，法律维权",
    },
    PRAction.PLAY_VICTIM: {
        "approval_delta": 6,
        "heat_delta": -3,
        "rumor_multiplier": 0.8,
        "brand_delta": -1,
        "description": "展示脆弱面，博取同情",
    },
    PRAction.COUNTERATTACK: {
        "approval_delta": -5,
        "heat_delta": 20,
        "rumor_multiplier": 0.4,
        "brand_delta": -3,
        "description": "强力反击，否认指控",
    },
    PRAction.HIDE: {
        "approval_delta": -3,
        "heat_delta": 3,
        "rumor_multiplier": 1.5,
        "brand_delta": -2,
        "description": "暂时隐退，避开公众视线",
    },
    PRAction.CHARITY: {
        "approval_delta": 4,
        "heat_delta": -8,
        "rumor_multiplier": 0.6,
        "brand_delta": 2,
        "description": "参与公益活动，改善形象",
    },
    PRAction.COMEBACK: {
        "approval_delta": 2,
        "heat_delta": 10,
        "rumor_multiplier": 1.0,
        "brand_delta": 1,
        "description": "尝试复出，发布新作品",
    },
}


# ── 阶段修正系数 ──
# 值 > 1 表示该动作在这个阶段更有效，< 1 表示效果打折

PHASE_MODIFIERS: dict[CrisisPhase, dict[PRAction, float]] = {
    CrisisPhase.BREAKOUT: {
        PRAction.SILENCE: 1.0,
        PRAction.APOLOGIZE: 0.3,       # 太早道歉显得心虚
        PRAction.STATEMENT: 0.8,
        PRAction.GO_ON_SHOW: 0.2,      # 爆发期不适合上节目
        PRAction.LAWSUIT: 0.5,
        PRAction.PLAY_VICTIM: 0.4,
        PRAction.COUNTERATTACK: 0.6,
        PRAction.HIDE: 0.8,
        PRAction.CHARITY: 0.2,
        PRAction.COMEBACK: 0.1,
    },
    CrisisPhase.ESCALATION: {
        PRAction.SILENCE: 0.6,         # 发酵期沉默危险
        PRAction.APOLOGIZE: 0.6,
        PRAction.STATEMENT: 1.0,
        PRAction.GO_ON_SHOW: 0.5,
        PRAction.LAWSUIT: 0.7,
        PRAction.PLAY_VICTIM: 0.7,
        PRAction.COUNTERATTACK: 0.8,
        PRAction.HIDE: 0.7,
        PRAction.CHARITY: 0.3,
        PRAction.COMEBACK: 0.2,
    },
    CrisisPhase.PEAK: {
        PRAction.SILENCE: 0.4,         # 高峰期沉默 = 认罪
        PRAction.APOLOGIZE: 1.2,       # 最佳道歉时机
        PRAction.STATEMENT: 1.1,
        PRAction.GO_ON_SHOW: 0.9,
        PRAction.LAWSUIT: 0.8,
        PRAction.PLAY_VICTIM: 0.9,
        PRAction.COUNTERATTACK: 1.0,
        PRAction.HIDE: 0.5,
        PRAction.CHARITY: 0.5,
        PRAction.COMEBACK: 0.3,
    },
    CrisisPhase.MITIGATION: {
        PRAction.SILENCE: 0.8,
        PRAction.APOLOGIZE: 0.9,
        PRAction.STATEMENT: 0.7,
        PRAction.GO_ON_SHOW: 1.1,
        PRAction.LAWSUIT: 1.0,
        PRAction.PLAY_VICTIM: 0.6,
        PRAction.COUNTERATTACK: 0.7,
        PRAction.HIDE: 0.9,
        PRAction.CHARITY: 1.2,         # 应对期公益效果好
        PRAction.COMEBACK: 0.6,
    },
    CrisisPhase.RESOLUTION: {
        PRAction.SILENCE: 1.0,
        PRAction.APOLOGIZE: 0.5,
        PRAction.STATEMENT: 0.5,
        PRAction.GO_ON_SHOW: 1.0,
        PRAction.LAWSUIT: 0.8,
        PRAction.PLAY_VICTIM: 0.3,
        PRAction.COUNTERATTACK: 0.5,
        PRAction.HIDE: 1.0,
        PRAction.CHARITY: 1.3,         # 收尾期公益最有效
        PRAction.COMEBACK: 1.0,
    },
    CrisisPhase.AFTERMATH: {
        PRAction.SILENCE: 1.0,
        PRAction.APOLOGIZE: 0.3,
        PRAction.STATEMENT: 0.3,
        PRAction.GO_ON_SHOW: 0.8,
        PRAction.LAWSUIT: 0.5,
        PRAction.PLAY_VICTIM: 0.2,
        PRAction.COUNTERATTACK: 0.3,
        PRAction.HIDE: 1.0,
        PRAction.CHARITY: 1.2,
        PRAction.COMEBACK: 1.3,        # 余波期复出最安全
    },
}


class CrisisActionSpace:
    """公关动作空间"""

    def compute_effect(
        self,
        action: PRAction,
        phase: CrisisPhase,
        base_approval: float,
        personality: dict | None = None,
    ) -> dict:
        """计算动作的实际效果

        Args:
            action: 公关动作
            phase: 当前危机阶段
            base_approval: 当前口碑分 (0-100)
            personality: 性格修正 {"neuroticism": 0.7, "extraversion": 0.5, ...}

        Returns:
            {"approval_delta", "heat_delta", "rumor_multiplier", "brand_delta",
             "actual_description"}
        """
        base = ACTION_EFFECTS.get(action, ACTION_EFFECTS[PRAction.SILENCE])
        phase_mod = PHASE_MODIFIERS.get(phase, {}).get(action, 1.0)

        # 性格修正
        pers_mod = 1.0
        if personality:
            neuroticism = personality.get("neuroticism", 0.5)
            extraversion = personality.get("extraversion", 0.5)
            agreeableness = personality.get("agreeableness", 0.5)

            if action == PRAction.COUNTERATTACK:
                pers_mod *= 1 + neuroticism * 0.3    # 神经质→反击更冲动
            elif action == PRAction.APOLOGIZE:
                pers_mod *= 1 + agreeableness * 0.2  # 随和→道歉更真诚
            elif action == PRAction.GO_ON_SHOW:
                pers_mod *= 1 + extraversion * 0.2   # 外向→上节目更自然
            elif action == PRAction.SILENCE:
                pers_mod *= 1 - extraversion * 0.2   # 外向→沉默更反常

        # 低口碑时修复更难
        if base_approval < 30 and action in (PRAction.APOLOGIZE, PRAction.STATEMENT):
            pers_mod *= 0.7

        modifier = phase_mod * pers_mod

        return {
            "approval_delta": round(base["approval_delta"] * modifier, 1),
            "heat_delta": round(base["heat_delta"] * modifier, 1),
            "rumor_multiplier": round(
                1 + (base["rumor_multiplier"] - 1) * modifier, 2
            ),
            "brand_delta": round(base["brand_delta"] * modifier, 1),
            "description": base["description"],
            "modifier": round(modifier, 2),
        }

    def get_available_actions(self, phase: CrisisPhase) -> list[dict]:
        """返回当前阶段的可用动作及效果预览"""
        results = []
        for action in PRAction:
            effect = self.compute_effect(action, phase, 50.0)
            phase_mod = PHASE_MODIFIERS.get(phase, {}).get(action, 1.0)
            results.append({
                "action": action.value,
                "label": action.label,
                "effectiveness": round(phase_mod, 2),
                "approval_delta": effect["approval_delta"],
                "heat_delta": effect["heat_delta"],
                "description": effect["description"],
            })
        results.sort(key=lambda x: x["effectiveness"], reverse=True)
        return results
