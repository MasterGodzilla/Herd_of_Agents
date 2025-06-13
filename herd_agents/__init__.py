"""
Herd of Agents - A multi-agent system framework

This package provides a framework for creating autonomous agents that can:
- Spawn child agents for subtasks
- Communicate via broadcasting and direct messaging
- Terminate themselves when tasks are complete
- Integrate custom tools and capabilities
"""

from .agent import Agent
from .tool_agent import ToolAgent
from .manager import AgentManager
from .message_bus import MessageBus
from .api import chat_complete, API_DOCS

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "ToolAgent",
    "AgentManager", 
    "MessageBus",
    "chat_complete",
    "API_DOCS",
] 