#!/usr/bin/env python3
"""
Simple Herd of Agents Example

This shows the most basic way to use the agent system:
1. Import the package
2. Create a manager
3. Create an agent with a mission
4. Run it

Run with: python examples/simple_example.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from herd_agents import AgentManager

async def main():
    # Create the agent manager
    manager = AgentManager()
    
    # Create a simple agent with a mission
    agent = await manager.create_genesis_agent(
        mission="Write a short poem about coding",
        model_name="gemini-2.5-flash"
    )
    
    # Start the system
    await manager.start()
    
    # Let it run for 30 seconds
    print("🤖 Agent system starting...")
    await manager.wait_for_convergence(timeout=30)
    
    # Stop the system
    await manager.stop()
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main()) 