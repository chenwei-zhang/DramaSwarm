# -*- coding: utf-8 -*-
"""
公关动作空间 - 10 种 PR 策略及其效果矩阵

每个动作对 approval/heat/rumor/brand 有不同影响，且受危机阶段修正。
"""

from __future__ import annotations

from swarmsim.crisis.models import CrisisPhase, PRAction, FreeAction


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
            risk_tolerance = personality.get("risk_tolerance", 0.5)
            public_visibility = personality.get("public_visibility", 0.5)
            media_savvy = personality.get("media_savvy", 0.5)
            controversy_history = personality.get("controversy_history", 0.3)

            if action == PRAction.COUNTERATTACK:
                pers_mod *= 1 + neuroticism * 0.3    # 神经质→反击更冲动
                pers_mod *= 1 + risk_tolerance * 0.2  # 高风险容忍→反击更猛
            elif action == PRAction.APOLOGIZE:
                pers_mod *= 1 + agreeableness * 0.2  # 随和→道歉更真诚
            elif action == PRAction.GO_ON_SHOW:
                pers_mod *= 1 + extraversion * 0.2   # 外向→上节目更自然
                pers_mod *= 1 + media_savvy * 0.15   # 媒体素养→上节目更得体
            elif action == PRAction.SILENCE:
                pers_mod *= 1 - extraversion * 0.2   # 外向→沉默更反常
                pers_mod *= 1 - public_visibility * 0.15  # 高曝光→沉默代价更大
            elif action == PRAction.STATEMENT:
                pers_mod *= 1 + media_savvy * 0.2    # 媒体素养→声明更有效
            elif action == PRAction.PLAY_VICTIM:
                pers_mod *= 1 + risk_tolerance * 0.15  # 冒险倾向→敢卖惨
            elif action == PRAction.CHARITY:
                pers_mod *= 1 + agreeableness * 0.15  # 随和→公益更自然
            elif action == PRAction.LAWSUIT:
                pers_mod *= 1 + (1 - agreeableness) * 0.1  # 不随和→倾向法律

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


# ── 自由互动动作效果 ──

FREE_ACTION_EFFECTS: dict[FreeAction, dict] = {
    FreeAction.SPEAK: {
        "approval_delta": 1, "heat_delta": 3, "brand_delta": 0,
        "description": "公开发言",
    },
    FreeAction.SUPPORT: {
        "approval_delta": 3, "heat_delta": 2, "brand_delta": 2,
        "description": "公开支持",
    },
    FreeAction.CRITICIZE: {
        "approval_delta": -2, "heat_delta": 5, "brand_delta": -1,
        "description": "公开批评",
    },
    FreeAction.COLLABORATE: {
        "approval_delta": 4, "heat_delta": 2, "brand_delta": 3,
        "description": "宣布合作",
    },
    FreeAction.SOCIALIZE: {
        "approval_delta": 2, "heat_delta": 3, "brand_delta": 1,
        "description": "参加社交活动",
    },
    FreeAction.ANNOUNCE: {
        "approval_delta": 2, "heat_delta": 8, "brand_delta": 1,
        "description": "发布重要声明",
    },
    FreeAction.IGNORE: {
        "approval_delta": -1, "heat_delta": -2, "brand_delta": 0,
        "description": "无视事件",
    },
    FreeAction.PRIVATE_MSG: {
        "approval_delta": 1, "heat_delta": 0, "brand_delta": 1,
        "description": "私下联系",
    },
    FreeAction.MEDIATE: {
        "approval_delta": 5, "heat_delta": -3, "brand_delta": 3,
        "description": "调停争端",
    },
    FreeAction.RUMOR: {
        "approval_delta": -3, "heat_delta": 8, "brand_delta": -2,
        "description": "传播消息",
    },
    FreeAction.RETREAT: {
        "approval_delta": -1, "heat_delta": -1, "brand_delta": -1,
        "description": "低调回避",
    },
}


# ── 自由动作阶段修正系数 ──

FREE_PHASE_MODIFIERS: dict[CrisisPhase, dict[FreeAction, float]] = {
    CrisisPhase.BREAKOUT: {
        FreeAction.SPEAK: 0.6,        # 爆发期发言容易引火烧身
        FreeAction.SUPPORT: 0.5,      # 急于站队风险大
        FreeAction.CRITICIZE: 0.8,
        FreeAction.COLLABORATE: 0.3,
        FreeAction.SOCIALIZE: 0.3,    # 危机当前社交活动不合时宜
        FreeAction.ANNOUNCE: 0.7,
        FreeAction.IGNORE: 1.0,
        FreeAction.PRIVATE_MSG: 1.0,
        FreeAction.MEDIATE: 0.4,
        FreeAction.RUMOR: 1.2,        # 爆发期谣言传播最快
        FreeAction.RETREAT: 0.8,
    },
    CrisisPhase.ESCALATION: {
        FreeAction.SPEAK: 0.8,
        FreeAction.SUPPORT: 0.7,
        FreeAction.CRITICIZE: 1.0,
        FreeAction.COLLABORATE: 0.5,
        FreeAction.SOCIALIZE: 0.4,
        FreeAction.ANNOUNCE: 0.9,
        FreeAction.IGNORE: 0.8,
        FreeAction.PRIVATE_MSG: 1.0,
        FreeAction.MEDIATE: 0.6,
        FreeAction.RUMOR: 1.0,
        FreeAction.RETREAT: 0.9,
    },
    CrisisPhase.PEAK: {
        FreeAction.SPEAK: 1.0,
        FreeAction.SUPPORT: 1.0,
        FreeAction.CRITICIZE: 1.2,    # 高峰期批评效果放大
        FreeAction.COLLABORATE: 0.5,
        FreeAction.SOCIALIZE: 0.3,
        FreeAction.ANNOUNCE: 1.1,
        FreeAction.IGNORE: 0.6,       # 高峰期无视代价大
        FreeAction.PRIVATE_MSG: 0.8,
        FreeAction.MEDIATE: 0.8,
        FreeAction.RUMOR: 1.0,
        FreeAction.RETREAT: 0.7,
    },
    CrisisPhase.MITIGATION: {
        FreeAction.SPEAK: 1.0,
        FreeAction.SUPPORT: 1.1,
        FreeAction.CRITICIZE: 0.8,
        FreeAction.COLLABORATE: 1.0,
        FreeAction.SOCIALIZE: 0.8,
        FreeAction.ANNOUNCE: 0.9,
        FreeAction.IGNORE: 1.0,
        FreeAction.PRIVATE_MSG: 1.0,
        FreeAction.MEDIATE: 1.2,      # 应对期调停效果最好
        FreeAction.RUMOR: 0.7,
        FreeAction.RETREAT: 1.0,
    },
    CrisisPhase.RESOLUTION: {
        FreeAction.SPEAK: 0.9,
        FreeAction.SUPPORT: 1.0,
        FreeAction.CRITICIZE: 0.6,
        FreeAction.COLLABORATE: 1.2,  # 收尾期合作修复关系效果好
        FreeAction.SOCIALIZE: 1.0,
        FreeAction.ANNOUNCE: 0.8,
        FreeAction.IGNORE: 1.0,
        FreeAction.PRIVATE_MSG: 1.0,
        FreeAction.MEDIATE: 1.0,
        FreeAction.RUMOR: 0.5,
        FreeAction.RETREAT: 1.0,
    },
    CrisisPhase.AFTERMATH: {
        FreeAction.SPEAK: 0.8,
        FreeAction.SUPPORT: 0.9,
        FreeAction.CRITICIZE: 0.4,
        FreeAction.COLLABORATE: 1.3,  # 余波期合作最有效
        FreeAction.SOCIALIZE: 1.1,
        FreeAction.ANNOUNCE: 0.7,
        FreeAction.IGNORE: 1.0,
        FreeAction.PRIVATE_MSG: 1.0,
        FreeAction.MEDIATE: 0.8,
        FreeAction.RUMOR: 0.3,
        FreeAction.RETREAT: 1.0,
    },
}


class FreeActionSpace:
    """自由互动动作空间"""

    def compute_effect(
        self,
        action: FreeAction,
        phase: CrisisPhase | None = None,
        base_approval: float = 50.0,
        personality: dict | None = None,
    ) -> dict:
        """计算自由动作效果（含阶段修正）"""
        base = FREE_ACTION_EFFECTS.get(action, FREE_ACTION_EFFECTS[FreeAction.IGNORE])

        # 阶段修正
        phase_mod = 1.0
        if phase:
            phase_mod = FREE_PHASE_MODIFIERS.get(phase, {}).get(action, 1.0)

        # 性格修正
        pers_mod = 1.0
        if personality:
            extraversion = personality.get("extraversion", 0.5)
            agreeableness = personality.get("agreeableness", 0.5)
            public_visibility = personality.get("public_visibility", 0.5)
            neuroticism = personality.get("neuroticism", 0.5)
            risk_tolerance = personality.get("risk_tolerance", 0.5)
            openness = personality.get("openness", 0.5)

            if action == FreeAction.SPEAK:
                pers_mod *= 1 + extraversion * 0.2
            elif action == FreeAction.SUPPORT:
                pers_mod *= 1 + agreeableness * 0.2
            elif action == FreeAction.CRITICIZE:
                pers_mod *= 1 + (1 - agreeableness) * 0.15
                pers_mod *= 1 + neuroticism * 0.1
            elif action == FreeAction.IGNORE:
                pers_mod *= 1 - public_visibility * 0.1
            elif action == FreeAction.MEDIATE:
                pers_mod *= 1 + agreeableness * 0.3
            elif action == FreeAction.ANNOUNCE:
                pers_mod *= 1 + extraversion * 0.15
            elif action == FreeAction.COLLABORATE:
                pers_mod *= 1 + openness * 0.15
            elif action == FreeAction.SOCIALIZE:
                pers_mod *= 1 + extraversion * 0.2
            elif action == FreeAction.PRIVATE_MSG:
                pers_mod *= 1 + agreeableness * 0.1
            elif action == FreeAction.RUMOR:
                pers_mod *= 1 + (1 - agreeableness) * 0.2
                pers_mod *= 1 + risk_tolerance * 0.15
            elif action == FreeAction.RETREAT:
                pers_mod *= 1 - extraversion * 0.1

        # 低口碑时正面动作效果打折
        if base_approval < 30 and action in (
            FreeAction.SUPPORT, FreeAction.COLLABORATE, FreeAction.SOCIALIZE,
        ):
            pers_mod *= 0.7

        modifier = phase_mod * pers_mod

        return {
            "approval_delta": round(base["approval_delta"] * modifier, 1),
            "heat_delta": round(base["heat_delta"] * modifier, 1),
            "brand_delta": round(base["brand_delta"] * modifier, 1),
            "description": base["description"],
            "modifier": round(modifier, 2),
        }
