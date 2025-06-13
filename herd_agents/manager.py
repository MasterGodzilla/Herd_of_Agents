import threading
import queue
import time
from typing import Dict, List, Optional
from datetime import datetime
from .agent import Agent
from .message_bus import MessageBus
from .api import chat_complete

class AgentManager:
    """Manages the lifecycle of multiple agents in parallel threads."""
    
    def __init__(self):
        """Initialize manager for parallel execution."""
        # Threading setup - no need for mp.Manager anymore
        self.message_bus = MessageBus()
        
        # Thread tracking
        self.threads: Dict[str, threading.Thread] = {}
        
        # Manager queue for agent requests - regular queue
        self.manager_queue = queue.Queue()
        
        # Agent registry - regular dict
        self.agent_registry = {}
        self.agents: Dict[str, Agent] = {}
        
        # Monitor thread
        self.monitor_thread = None
        self.running = False
        
        # Agent summaries - shared knowledge to avoid repetition
        self.agent_summaries: Dict[str, str] = {}
        
        # Metrics
        self.total_agents_created = 0
        self.total_agents_died = 0
        self.start_time = None
    
    def register_agent(self, agent: Agent):
        """Register a new agent with the system."""
        # Set up agent for parallel execution
        agent.message_bus = self.message_bus
        agent.manager_queue = self.manager_queue
        agent.manager = self
        
        # Register with message bus
        self.message_bus.register_agent(agent.id)
        
        # Update registries
        self.agents[agent.id] = agent
        self.agent_registry[agent.id] = {
            'id': agent.id,
            'mission': agent.mission,
            'parent_id': agent.parent_id,
            'alive': True
        }
        self.agent_summaries[agent.id] = f"New agent working on: {agent.mission}"
        
        # Start agent thread if manager is running
        if self.running:
            thread = threading.Thread(target=agent.run, name=f"Agent-{agent.id}")
            thread.daemon = True  # Make threads daemon so they exit when main exits
            thread.start()
            self.threads[agent.id] = thread
        
        self.total_agents_created += 1
        print(f"[Manager] Registered agent {agent.id}: {agent.mission}")
    
    def unregister_agent(self, agent_id: str):
        """Remove agent from the system."""
        if agent_id in self.agents:
            # Generate final summary before removing
            self.update_agent_summary(agent_id)
            
            # Thread cleanup
            if agent_id in self.threads:
                thread = self.threads[agent_id]
                # Threads can't be forcefully terminated in Python
                # The agent should terminate itself gracefully
                del self.threads[agent_id]
            
            # Update registry
            if agent_id in self.agent_registry:
                del self.agent_registry[agent_id]
            
            # Common cleanup
            self.message_bus.unregister_agent(agent_id)
            del self.agents[agent_id]
            
            self.total_agents_died += 1
            print(f"[Manager] Unregistered agent {agent_id}")
    
    def get_agent_summary(self, agent_id: str) -> str:
        """Get the summary for an agent."""
        return self.agent_summaries.get(agent_id, "No summary available")
    
    def update_agent_summary(self, agent_id: str):
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
    
    def create_genesis_agent(self, mission: str, model_name: str = "gemini-2.5-flash") -> Agent:
        """Create the first agent to bootstrap the system."""
        genesis = Agent(
            agent_id="genesis",
            mission=mission,
            model_name=model_name
        )
        self.register_agent(genesis)
        return genesis
    
    def start(self):
        """Start all agent lifecycles."""
        self.running = True
        self.start_time = datetime.now()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self.monitor, name="Manager-Monitor")
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Start all existing agents
        for agent in self.agents.values():
            thread = threading.Thread(target=agent.run, name=f"Agent-{agent.id}")
            thread.daemon = True
            thread.start()
            self.threads[agent.id] = thread
        
        print(f"[Manager] Started with {len(self.agents)} agents")
    
    def monitor(self):
        """Monitor manager queue for agent requests."""
        while self.running:
            try:
                request = self.manager_queue.get(timeout=0.1)
                
                if request['type'] == 'spawn':
                    # Dynamically import and create the agent class
                    module_name = request.get('agent_class_module', 'herd_agents.agent')
                    class_name = request.get('agent_class_name', 'Agent')
                    
                    # Import the module and get the class
                    import importlib
                    module = importlib.import_module(module_name)
                    agent_class = getattr(module, class_name)
                    
                    # Create agent using the class's factory method
                    child = agent_class.from_spawn_data(request)
                    self.register_agent(child)
                    
                elif request['type'] == 'terminate':
                    # Clean up terminated agent
                    agent_id = request['agent_id']
                    self.unregister_agent(agent_id)
                    
            except queue.Empty:
                pass
            except Exception as e:
                print(f"[Manager] Error in monitor: {e}")
    
    def stop(self):
        """Gracefully stop all agents."""
        self.running = False
        
        # Send stop signal to all agents
        stop_msg = {
            "from": "manager",
            "to": "broadcast",
            "content": "SYSTEM SHUTDOWN",
            "timestamp": datetime.now().isoformat()
        }
        self.message_bus.publish_sync(stop_msg)
        
        # Wait a bit for agents to terminate gracefully
        time.sleep(1)
        
        # Stop monitor thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        
        # Wait for threads to finish
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=1)
        
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
    
    def wait_for_convergence(self, timeout: Optional[float] = None) -> bool:
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
            
            time.sleep(0.5) 