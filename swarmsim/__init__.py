"""
SwarmSim - Multi-Agent Simulation Engine

A lightweight multi-agent swarm intelligence engine focused on
simulating complex social scenarios and group dynamics.
"""

__version__ = "0.1.0"
__author__ = "SwarmSim Team"

from swarmsim.core.agent import Agent, AgentState
from swarmsim.core.environment import Environment
from swarmsim.core.event_loop import EventLoop
from swarmsim.core.factory import AgentFactory
from swarmsim.core.observer import Observer

__all__ = [
    "Agent",
    "AgentState",
    "Environment",
    "EventLoop",
    "AgentFactory",
    "Observer",
]
