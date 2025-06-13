#!/usr/bin/env python3
"""Interactive terminal interface for Herd of Agents"""

import sys
import os

# Set DEBUG before imports
os.environ["DEBUG"] = "true"

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from herd_agents import AgentManager
from herd_agents.agent import Agent

def main():
    """Main interactive function."""
    print("\n🐑 HERD OF AGENTS - Interactive Mode 🐑\n")
    print("This system spawns autonomous LLM agents that collaborate dynamically.")
    print("Agents can spawn children, broadcast findings, and self-terminate.\n")
    
    # Get mission from user
    mission = input("What would you like the agents to work on? (or 'quit' to exit)\n> ").strip()
    
    if mission.lower() in ['quit', 'exit', 'q']:
        print("Goodbye!")
        return
        
    if not mission:
        mission = "Spawn two agents, tell them to each spawn two agents, and report back their mood for the day."
        print(f"Using default mission: {mission}")
    
    # Create the agent manager
    manager = AgentManager()
    
    # Create genesis agent
    genesis = Agent(
        agent_id="genesis",
        mission=mission,
        model_name="gemini-2.5-pro"  # Fast model for demo
    )
    
    # Register the agent
    manager.register_agent(genesis)
    
    # Start the system
    print(f"\n🚀 Starting agent system with mission: '{mission}'")
    print("Watch for [DEBUG] messages to see agent communication...\n")
    
    manager.start()
    
    # Wait for completion
    print("🤖 Agent swarm starting...")
    print("-" * 50)
    
    try:
        timeout = 600 # 10 minutes
        converged = manager.wait_for_convergence(timeout=timeout)
        
        if converged:
            print("\n✅ SYSTEM CONVERGED - All agents completed their tasks")
        else:
            print("\n⏹️ SYSTEM STOPPED")
            
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user - shutting down...")
    
    # Stop the system
    manager.stop()
    
    # Print final status
    print("\n" + "="*50)
    print("FINAL SYSTEM STATE")
    print("="*50)
    manager.print_status()
    
    # Show agent summaries if available
    if hasattr(manager, 'agent_summaries') and manager.agent_summaries:
        print("\nAgent Summaries:")
        for agent_id, summary in manager.agent_summaries.items():
            print(f"  [{agent_id}]: {summary}")
    
    print("✅ Done!")

def run_loop():
    """Run the interactive loop."""
    while True:
        try:
            main()
            
            # Ask if they want to run again
            again = input("\n\nRun another mission? (y/n) > ").strip().lower()
            if again not in ['y', 'yes']:
                break
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
    
    print("\nThanks for using Herd of Agents! 🐑")

if __name__ == "__main__":
    try:
        run_loop()
    except KeyboardInterrupt:
        print("\nGoodbye!") 