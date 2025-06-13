#!/usr/bin/env python3
"""
Tool Integration Example

This example shows how to:
1. Define custom tools
2. Create tool documentation
3. Create agents with tool support
4. Let agents use tools to complete tasks

Run with: python examples/tool_example.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from herd_agents import AgentManager
from herd_agents.tool_agent import ToolAgent

# Define simple tools
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Safe evaluation of math expressions
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"

def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Tool documentation that will be added to system prompt
TOOL_DOCS = """
1. calculate(expression) - Evaluate mathematical expressions
   Example: [TOOL: calculate(2 + 2 * 3)]
   Returns: The numerical result

2. get_time() - Get the current date and time
   Example: [TOOL: get_time()]
   Returns: Current timestamp
"""

# Define available tools
TOOLS = {
    "calculate": calculate,
    "get_time": get_time
}

async def main():
    # Create the agent manager
    manager = AgentManager()
    
    # Create a tool-enabled agent with a mission that needs tools
    agent = ToolAgent(
        agent_id="calculator",
        mission="Calculate the sum of squares from 1 to 5 (1² + 2² + 3² + 4² + 5²) and tell me what time you finished",
        model_name="gemini-2.5-flash",
        tools=TOOLS,
        tool_docs=TOOL_DOCS
    )
    
    # Register the agent
    await manager.register_agent(agent)
    
    # Start the system
    await manager.start()
    
    # Let it run
    print("🤖 Tool-enabled agent starting...")
    print(f"📋 Mission: {agent.mission}")
    print("🛠️  Available tools: calculate, get_time")
    print("-" * 50)
    
    # Wait for completion
    await manager.wait_for_convergence(timeout=30)
    
    # Stop the system
    await manager.stop()
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(main()) 