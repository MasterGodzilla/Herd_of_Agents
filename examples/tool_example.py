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
        # Safe evaluation with basic math functions
        safe_dict = {
            "__builtins__": {},
            "sum": sum,
            "range": range,
            "pow": pow,
            "abs": abs,
            "min": min,
            "max": max
        }
        result = eval(expression, safe_dict)
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
   Examples: 
   - [TOOL: calculate(2 + 2 * 3)]
   - [TOOL: calculate(sum(i**3 for i in range(1, 11)))]
   Supports: basic math, sum(), range(), pow(), etc.
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
    
    # Create a tool-enabled agent with a mission that demonstrates spawning, calculation, and aggregation
    agent = ToolAgent(
        agent_id="coordinator",
        mission="""Calculate the sum of cubes for three ranges and find the grand total:
        1. Range 1-10: calculate sum of n³ for each n
        2. Range 11-20: calculate sum of n³ for each n  
        3. Range 21-30: calculate sum of n³ for each n
        
        Spawn child agents to handle each range in parallel, then aggregate their results.
        REPORT the final grand total and when you finished to the human.""",
        model_name="gemini-2.5-flash",
        tools=TOOLS,
        tool_docs=TOOL_DOCS
    )
    
    # Register the agent
    await manager.register_agent(agent)
    
    # Start the system
    await manager.start()
    
    # Let it run
    print("🤖 Swarm calculation with tools starting...")
    print("📋 Mission: Calculate sum of cubes across ranges using parallel agents")
    print("🛠️  Available tools: calculate, get_time")
    print("-" * 50)
    
    # Wait for completion (give more time for multi-agent coordination)
    await manager.wait_for_convergence(timeout=60)
    
    # Stop the system
    await manager.stop()
    
    # Print final status
    print("\n" + "="*50)
    manager.print_status()
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main()) 