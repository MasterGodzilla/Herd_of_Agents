"""Basic test to verify agent system works"""
import time
from herd_agents import AgentManager

def test_basic():
    """Test basic agent spawning and communication using threading approach"""
    print("Testing basic agent system...")
    
    # Create the agent manager
    manager = AgentManager()
    
    # Create a genesis agent with a simple mission
    genesis = manager.create_genesis_agent(
        mission="Spawn two agents, tell them to say hello to each other, and report back their mood for the day."
    )
    
    print(f"Created genesis agent: {genesis.agent_id}")
    print(f"Mission: {genesis.mission}")
    
    # Start the system (begins threading)
    print("\nStarting agent system...")
    manager.start()
    
    # Wait for convergence with timeout
    print("Waiting for agents to complete their work...")
    converged = manager.wait_for_convergence(timeout=30)
    
    if converged:
        print("✅ System converged successfully!")
    else:
        print("⏰ System timed out - stopping anyway")
    
    # Print final status
    print("\nFinal system state:")
    manager.print_status()
    
    # Stop the system
    manager.stop()
    print("✅ Test completed!")

if __name__ == "__main__":
    test_basic() 