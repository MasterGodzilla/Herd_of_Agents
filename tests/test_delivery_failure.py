"""Test delivery failure notifications when messaging dead agents"""
import asyncio
import os
os.environ["DEBUG"] = "true"  # Set before imports

from agent_manager import AgentManager

async def test_delivery_failure():
    manager = AgentManager()
    
    # Create two agents
    agent1 = await manager.create_genesis_agent(
        mission="Wait for a message from agent2, then try to reply after agent2 dies"
    )
    
    # Start system
    await manager.start()
    
    # Give agents time to start
    await asyncio.sleep(2)
    
    # Manually spawn agent2 and have it message agent1 then die
    agent2_mission = "Send a message to genesis saying 'Hello!', then immediately terminate"
    await agent1.spawn(agent2_mission)
    
    # Let the scenario play out
    await asyncio.sleep(10)
    
    # Stop system
    await manager.stop()
    
    print("\n=== TEST COMPLETE ===")
    print("Agent1 should have received a delivery failure notification after trying to reply to dead agent2")

if __name__ == "__main__":
    print("Testing delivery failure notifications...")
    asyncio.run(test_delivery_failure()) 