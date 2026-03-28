# -*- coding: utf-8 -*-
"""
危机时间线 - 1 turn = 1 天

将仿真回合映射到真实日期，按阶段划分危机生命周期。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from swarmsim.crisis.models import CrisisPhase


class CrisisTimeline:
    """危机时间线：1 turn = 1 真实天"""

    def __init__(self, start_date: str, total_days: int = 30):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.current_day = 0
        self.total_days = total_days

    def current_date(self) -> str:
        """当前仿真日期"""
        return (self.start_date + timedelta(days=self.current_day)).strftime("%Y-%m-%d")

    def current_date_obj(self) -> datetime:
        return self.start_date + timedelta(days=self.current_day)

    def advance_day(self) -> CrisisPhase:
        """推进一天，返回新阶段"""
        self.current_day += 1
        return self.get_phase()

    def get_phase(self) -> CrisisPhase:
        """从天数映射到危机阶段"""
        day = self.current_day
        if day <= 1:
            return CrisisPhase.BREAKOUT
        elif day <= 3:
            return CrisisPhase.ESCALATION
        elif day <= 7:
            return CrisisPhase.PEAK
        elif day <= 14:
            return CrisisPhase.MITIGATION
        elif day <= 21:
            return CrisisPhase.RESOLUTION
        else:
            return CrisisPhase.AFTERMATH

    def is_finished(self) -> bool:
        return self.current_day >= self.total_days

    def day_label(self) -> str:
        """中文日期标签"""
        phase = self.get_phase()
        return f"第{self.current_day}天 ({phase.label}) {self.current_date()}"

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "current_day": self.current_day,
            "current_date": self.current_date(),
            "total_days": self.total_days,
            "phase": self.get_phase().value,
            "phase_label": self.get_phase().label,
            "is_finished": self.is_finished(),
        }
