# -*- coding: utf-8 -*-
"""
商业品牌层 - 品牌代言、商业价值、解约
"""

from __future__ import annotations

import random

from ..models import (
    ReactionEvent, BrandStatus,
    BrandAction
)
from .base import ReactionLayer


# 品牌名称池
BRAND_POOL = [
    "某国际化妆品", "某运动品牌", "某手机品牌", "某汽车品牌",
    "某快消品牌", "某奢侈品", "某饮料品牌", "某服装品牌",
]


class CommercialLayer(ReactionLayer):
    """商业品牌反应层"""

    layer_name = "commercial"

    def __init__(self):
        self.brand_statuses: dict[str, BrandStatus] = {}   # agent_id -> status
        self.global_revenue_impact: float = 0.0

    def register_agent(self, agent_id: str, agent_name: str,
                       initial_value: float = 60.0, brands: list[str] | None = None):
        """注册明星的商业信息"""
        active_brands = brands or random.sample(BRAND_POOL, random.randint(1, 3))
        self.brand_statuses[agent_id] = BrandStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            active_brands=active_brands,
            commercial_value=initial_value,
            brand_actions={b: BrandAction.CONTINUE for b in active_brands},
        )

    def react(self, event_description: str, severity: float,
              source: str, context: dict) -> list[ReactionEvent]:
        reactions = []

        # 获取公众舆论层的好感度变化
        approval_scores = context.get("approval_scores", {})

        for agent_id, status in self.brand_statuses.items():
            if status.agent_name not in event_description and source != status.agent_name:
                continue

            # 计算好感度影响
            approval = approval_scores.get(status.agent_name, 60)
            old_value = status.commercial_value

            # 商业价值 = 好感度 * 0.6 + 50 * 0.4（基础分）
            status.commercial_value = max(0, approval * 0.6 + 20)

            value_drop = old_value - status.commercial_value

            # 品牌反应
            for brand in status.active_brands:
                old_action = status.brand_actions.get(brand, BrandAction.CONTINUE)
                new_action = self._determine_brand_action(old_action, value_drop, severity)
                status.brand_actions[brand] = new_action

                if new_action != old_action and new_action != BrandAction.CONTINUE:
                    reactions.append(ReactionEvent(
                        source_event_id=context.get("event_id", ""),
                        reaction_layer=self.layer_name,
                        severity=value_drop / 100,
                        target_agent_ids=[agent_id],
                        description=f"{brand}对{status.agent_name}态度变化: "
                                    f"{self._action_label(old_action)} → {self._action_label(new_action)}",
                    ))

            # 收入影响
            if value_drop > 0:
                impact = value_drop * random.uniform(100, 500)  # 万元
                status.revenue_impact -= impact
                self.global_revenue_impact -= impact

        return reactions

    def _determine_brand_action(self, current: BrandAction,
                                 value_drop: float, severity: float) -> BrandAction:
        """根据好感度下降决定品牌态度"""
        if value_drop > 30 or severity > 0.8:
            return BrandAction.TERMINATED
        elif value_drop > 20 or severity > 0.6:
            return BrandAction.SUSPENDED
        elif value_drop > 10 or severity > 0.4:
            return BrandAction.NEGOTIATING
        elif value_drop > 5 or severity > 0.3:
            return BrandAction.MONITORING
        elif current in (BrandAction.MONITORING, BrandAction.NEGOTIATING):
            # 情况好转时逐步恢复
            if value_drop <= 0:
                return BrandAction.CONTINUE
        return current

    def _action_label(self, action: BrandAction) -> str:
        labels = {
            BrandAction.CONTINUE: "继续合作",
            BrandAction.MONITORING: "观望中",
            BrandAction.NEGOTIATING: "重新谈判",
            BrandAction.SUSPENDED: "暂停合作",
            BrandAction.TERMINATED: "已解约",
            BrandAction.LAWSUIT: "索赔起诉",
        }
        return labels.get(action, str(action))

    def decay(self):
        """商业价值缓慢恢复"""
        for status in self.brand_statuses.values():
            if status.commercial_value < 60:
                status.commercial_value += 0.5  # 缓慢恢复

    def get_state(self) -> dict:
        return {
            "brand_statuses": {
                s.agent_name: {
                    "commercial_value": f"{s.commercial_value:.0f}",
                    "brands": {b: self._action_label(a) for b, a in s.brand_actions.items()},
                    "revenue_impact": f"{s.revenue_impact:.0f}万",
                }
                for s in self.brand_statuses.values()
            },
        }

    def get_description(self) -> str:
        lines = ["【商业动态】"]
        has_action = False
        for status in self.brand_statuses.values():
            non_continue = {b: a for b, a in status.brand_actions.items()
                           if a != BrandAction.CONTINUE}
            if non_continue:
                has_action = True
                brands_str = "、".join(
                    f"{b}({self._action_label(a)})"
                    for b, a in non_continue.items()
                )
                lines.append(f"  {status.agent_name}: 商业价值{status.commercial_value:.0f} | {brands_str}")
        if not has_action:
            lines.append("  各品牌暂无动向")
        return "\n".join(lines)

    def reset(self):
        for status in self.brand_statuses.values():
            status.commercial_value = 60.0
            status.revenue_impact = 0.0
            status.brand_actions = {b: BrandAction.CONTINUE for b in status.active_brands}
        self.global_revenue_impact = 0.0
