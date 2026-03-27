# -*- coding: utf-8 -*-
"""
Environment 包 - 多层反应系统

提供 Environment, VarietyShowEnvironment 及所有反应层。
"""

from .base import Environment, EnvironmentEvent, EnvironmentState, WeatherCondition
from .variety_show import VarietyShowEnvironment
from .reaction_bus import ReactionBus
from .models import (
    SentimentPolarity,
    FanReactionType,
    MediaType,
    RegulatoryAction,
    BrandAction,
    TrendingRankChange,
    ReactionEvent,
    NetizenSentiment,
    FanReaction,
    MediaCoverage,
    RegulatoryState,
    BrandStatus,
    TrendingTopic,
    EnvironmentReactionSnapshot,
)
from .layers import (
    PublicOpinionLayer,
    MediaLayer,
    SocialPlatformLayer,
    GovernmentLayer,
    CommercialLayer,
)

__all__ = [
    # Environment
    "Environment",
    "EnvironmentEvent",
    "EnvironmentState",
    "WeatherCondition",
    "VarietyShowEnvironment",
    # Reaction system
    "ReactionBus",
    # Models
    "SentimentPolarity",
    "FanReactionType",
    "MediaType",
    "RegulatoryAction",
    "BrandAction",
    "TrendingRankChange",
    "ReactionEvent",
    "NetizenSentiment",
    "FanReaction",
    "MediaCoverage",
    "RegulatoryState",
    "BrandStatus",
    "TrendingTopic",
    "EnvironmentReactionSnapshot",
    # Layers
    "PublicOpinionLayer",
    "MediaLayer",
    "SocialPlatformLayer",
    "GovernmentLayer",
    "CommercialLayer",
]
