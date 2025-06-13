import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from agent import Agent
from message_bus import MessageBus
from api import chat_complete

class AgentManager:
    """Manages the lifecycle of multiple agents and their communication."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_bus = MessageBus()
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        
        # Agent summaries - shared knowledge to avoid repetition
        self.agent_summaries: Dict[str, str] = {}
        
        # Metrics
        self.total_agents_created = 0
        self.total_agents_died = 0
        self.start_time = None
    
    async def register_agent(self, agent: Agent):
        """Register a new agent with the system."""
        self.agents[agent.id] = agent
        agent.message_bus = self.message_bus
        agent.manager = self
        
        # Register with message bus
        self.message_bus.register_agent(agent.id)
        
        # Initialize summary
        self.agent_summaries[agent.id] = f"New agent working on: {agent.mission}"
        
        # Start agent's lifecycle
        if self.running:
            task = asyncio.create_task(agent.lifecycle())
            self.tasks[agent.id] = task
        
        self.total_agents_created += 1
        print(f"[Manager] Registered agent {agent.id}: {agent.mission}")
    
    async def unregister_agent(self, agent_id: str):
        """Remove agent from the system."""
        if agent_id in self.agents:
            # Generate final summary before removing
            await self.update_agent_summary(agent_id)
            
            # Cancel task if running
            if agent_id in self.tasks:
                self.tasks[agent_id].cancel()
                del self.tasks[agent_id]
            
            # Unregister from message bus
            self.message_bus.unregister_agent(agent_id)
            
            # Remove from agents dict
            del self.agents[agent_id]
            
            self.total_agents_died += 1
            print(f"[Manager] Unregistered agent {agent_id}")
    
    async def get_agent_summary(self, agent_id: str) -> str:
        """Get the summary for an agent."""
        return self.agent_summaries.get(agent_id, "No summary available")
    
    async def update_agent_summary(self, agent_id: str):
        """Update an agent's summary using a separate LLM call."""
        if agent_id not in self.agents:
            return
            
        agent = self.agents[agent_id]
        
        # Don't summarize if no significant history
        if len(agent.context_history) < 4:  # Less than 2 exchanges
            return
        
        # Create a focused summarization prompt
        messages = [
            {
                "role": "system", 
                "content": "You are a concise summarizer. Extract only the KEY findings, decisions, and current status. Be extremely brief."
            },
            {
                "role": "user",
                "content": f"""Summarize this agent's work in 2-3 sentences MAX:
                
Agent ID: {agent.id}
Mission: {agent.mission}
Conversation history:
{agent.context_history}

Focus on: What has been discovered? What is being worked on now? What decisions were made?"""
            }
        ]
        
        # Get summary from LLM
        summary = chat_complete(messages, model_name=agent.model_name, max_tokens=150)
        
        # Update the shared summary
        self.agent_summaries[agent_id] = summary.strip()
        
        # Also update summaries visible to other agents
        for other_agent in self.agents.values():
            if other_agent.id != agent_id:
                # Update their view of who's active
                other_agent.active_agents = [
                    f"{a.id}: {self.agent_summaries.get(a.id, a.mission)[:50]}..." 
                    for a in self.get_active_agents() 
                    if a.id != other_agent.id
                ]
    
    async def create_genesis_agent(self, mission: str, model_name: str = "gemini-2.5-flash") -> Agent:
        """Create the first agent to bootstrap the system."""
        genesis = Agent(
            agent_id="genesis",
            mission=mission,
            model_name=model_name
        )
        await self.register_agent(genesis)
        return genesis
    
    async def start(self):
        """Start all agent lifecycles."""
        self.running = True
        self.start_time = datetime.now()
        
        # Start all existing agents
        for agent in self.agents.values():
            if agent.id not in self.tasks:
                task = asyncio.create_task(agent.lifecycle())
                self.tasks[agent.id] = task
        
        print(f"[Manager] Started with {len(self.agents)} agents")
    
    async def stop(self):
        """Gracefully stop all agents."""
        self.running = False
        
        # Send stop signal to all agents
        stop_msg = {
            "from": "manager",
            "to": "broadcast",
            "content": "SYSTEM SHUTDOWN",
            "timestamp": datetime.now().isoformat()
        }
        await self.message_bus.publish(stop_msg)
        
        # Wait a bit for agents to terminate gracefully
        await asyncio.sleep(1)
        
        # Cancel remaining tasks
        for task in self.tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        print(f"[Manager] Stopped. Total agents created: {self.total_agents_created}, died: {self.total_agents_died}")
    
    def get_active_agents(self) -> List[Agent]:
        """Get list of currently active agents."""
        return [agent for agent in self.agents.values() if agent.alive]
    
    def get_agent_tree(self) -> Dict:
        """Get hierarchical view of agent relationships."""
        tree = {}
        
        # Find root agents (no parent)
        roots = [agent for agent in self.agents.values() if agent.parent_id is None]
        
        def build_subtree(agent: Agent) -> Dict:
            subtree = {
                "id": agent.id,
                "mission": agent.mission,
                "alive": agent.alive,
                "messages_sent": agent.messages_sent,
                "summary": self.agent_summaries.get(agent.id, "No summary"),
                "children": []
            }
            
            # Add children
            for child_id in agent.children_ids:
                if child_id in self.agents:
                    subtree["children"].append(build_subtree(self.agents[child_id]))
            
            return subtree
        
        for root in roots:
            tree[root.id] = build_subtree(root)
        
        return tree
    
    def print_status(self):
        """Print current system status."""
        active = self.get_active_agents()
        runtime = (datetime.now() - self.start_time).seconds if self.start_time else 0
        
        print("\n=== Agent System Status ===")
        print(f"Runtime: {runtime}s")
        print(f"Active agents: {len(active)}/{self.total_agents_created}")
        print(f"Total died: {self.total_agents_died}")
        print(f"Message history: {len(self.message_bus.message_history)}")
        
        if active:
            print("\nActive Agents:")
            for agent in active:
                summary = self.agent_summaries.get(agent.id, "Working...")[:80]
                print(f"  - {agent.id}: {summary}...")
        
        print("========================\n")
    
    async def wait_for_convergence(self, timeout: Optional[float] = None) -> bool:
        """Wait for system to converge or timeout."""
        start = datetime.now()
        
        while True:
            # Check if all agents are dead (natural convergence)
            if not self.get_active_agents():
                print("[Manager] All agents terminated - system converged")
                return True
            
            # Check timeout
            if timeout and (datetime.now() - start).seconds > timeout:
                print("[Manager] Timeout reached")
                return False
            
            await asyncio.sleep(0.5) 