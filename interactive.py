#!/usr/bin/env python3
"""Interactive terminal interface for Herd of Agents"""

import os
# Enable debug mode to see all messages - MUST be set before importing agent modules
os.environ["DEBUG"] = "true"

import asyncio
import sys
from datetime import datetime
from agent_manager import AgentManager

async def monitor_system(manager: AgentManager, interval: float = 5.0):
    """Periodically print system status."""
    while manager.running:
        await asyncio.sleep(interval)
        print("\n" + "="*60)
        manager.print_status()
        
        # Show recent messages
        recent_msgs = manager.message_bus.get_history(limit=5)
        if recent_msgs:
            print("Recent Activity:")
            for msg in recent_msgs:
                timestamp = msg.get('timestamp', 'unknown')[:19]  # Just date and time
                print(f"  [{timestamp}] {msg.get('from', '?')} → {msg.get('to', '?')}: {msg.get('content', '')[:60]}...")
        print("="*60 + "\n")

async def run_interactive():
    """Main interactive loop."""
    print("\n🐑 HERD OF AGENTS - Interactive Mode 🐑\n")
    print("This system spawns autonomous LLM agents that collaborate dynamically.")
    print("Agents can spawn children, broadcast findings, and self-terminate.\n")
    
    # Get mission from user
    mission = input("What would you like the agents to work on? (or 'quit' to exit)\n> ").strip()
    
    if mission.lower() in ['quit', 'exit', 'q']:
        print("Goodbye!")
        return
        
    if not mission:
        mission = "Test spawning multiple agents and having them communicate"
        print(f"Using default mission: {mission}")
    
    # Get timeout
    timeout_str = input("\nHow many seconds should I let them work? (default: 60)\n> ").strip()
    try:
        timeout = int(timeout_str) if timeout_str else 60
    except ValueError:
        timeout = 60
        print("Using default timeout: 60 seconds")
    
    # Create and start system
    print(f"\n🚀 Starting agent system with mission: '{mission}'")
    print(f"⏱️  Will run for up to {timeout} seconds\n")
    print("Watch for [DEBUG] messages to see agent communication...\n")
    
    manager = AgentManager()
    
    # Create genesis agent
    genesis = await manager.create_genesis_agent(
        mission=mission,
        model_name="gemini-2.5-flash"  # Fast model for demo
    )
    
    # Start system
    await manager.start()
    
    # Start monitoring
    monitor_task = asyncio.create_task(monitor_system(manager, interval=10))
    
    try:
        # Wait for convergence or timeout
        converged = await manager.wait_for_convergence(timeout=timeout)
        
        if converged:
            print("\n✅ SYSTEM CONVERGED - All agents completed their tasks")
        else:
            print("\n⏰ TIMEOUT REACHED - Stopping agents")
        
        # Final status
        print("\n" + "="*60)
        print("FINAL SYSTEM STATE")
        print("="*60)
        manager.print_status()
        
        # Print agent tree
        print("\nAgent Hierarchy:")
        tree = manager.get_agent_tree()
        
        def print_tree(node, indent=0):
            prefix = "  " * indent
            status = "✓" if not node['alive'] else "●"
            print(f"{prefix}{status} {node['id']}: {node['mission'][:50]}...")
            if node['summary'] != "No summary":
                print(f"{prefix}  Summary: {node['summary'][:80]}...")
            for child in node['children']:
                print_tree(child, indent + 1)
        
        for root_id, root_node in tree.items():
            print_tree(root_node)
        
        # Show final summaries
        print("\n" + "="*60)
        print("AGENT SUMMARIES")
        print("="*60)
        for agent_id, summary in manager.agent_summaries.items():
            print(f"\n[{agent_id}]:")
            print(f"  {summary}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user - shutting down...")
    finally:
        # Clean shutdown
        monitor_task.cancel()
        await manager.stop()
        print("\n✅ System shut down cleanly")

async def main():
    """Main entry point with loop."""
    while True:
        try:
            await run_interactive()
            
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
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!") 