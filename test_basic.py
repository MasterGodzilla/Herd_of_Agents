"""Basic test to verify agent system works"""
import asyncio
from agent_manager import AgentManager

async def test_basic():
    manager = AgentManager()
    
    # Create a simple genesis agent
    genesis = await manager.create_genesis_agent(
        mission="Test if basic spawning and communication works"
    )
    
    # Start system
    await manager.start()
    
    # Let it run for a bit
    await asyncio.sleep(10)
    
    # Print status
    manager.print_status()
    
    # Stop
    await manager.stop()

if __name__ == "__main__":
    print("Testing basic agent system...")
    asyncio.run(test_basic()) 