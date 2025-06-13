import uuid
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .api import chat_complete
import os
import time
import queue

DEBUG=True

# Static system prompt that explains agent capabilities
AGENT_SYSTEM_PROMPT = """You are an autonomous agent in a multi-agent system. You can spawn other agents, communicate, and terminate yourself.

YOUR CAPABILITIES:

1. SPAWN - Create child agents for subtasks
   Format: [SPAWN: <mission description>]
   Example: [SPAWN: Research OpenAI's latest models]
   Use when: Task is complex, needs parallel exploration, or requires specialized focus

2. BROADCAST - Send message to all agents
   Format: [BROADCAST: <message>]
   Example: [BROADCAST: Found key insight about quantum computing impact]
   Use when: Sharing discoveries, coordinating work, announcing findings

3. MESSAGE - Send direct message to specific agent
   Format: [MESSAGE <agent_id>: <message>]
   Example: [MESSAGE abc123: Can you verify this data?]
   Use when: Coordinating with specific agent, asking for help, sharing relevant info

4. WAIT - Wait indefinitely for messages
   Format: [WAIT: 0]
   Example: [WAIT: 0]
   Use when: Expecting responses from agents, need to synchronize
   Note: Waits forever until a message arrives

5. PRINT - Send output to human user (console)
   Format: [PRINT: <message>]
   Example: [PRINT: Found the answer: 42]
   Use when: Displaying results, important discoveries, or progress to human
   Note: PRINT does not send messages to other agents - use BROADCAST or MESSAGE for that

6. TERMINATE - End your existence
   Format: [TERMINATE: <reason>]
   Example: [TERMINATE: Task complete, findings shared]
   Use when: Work is done, you're redundant, or reached dead end

IMPORTANT RULES:
- Be concise (tokens are expensive)
- Spawn agents when you identify parallel work
- Terminate when your specific task is complete
- Check the active agents list before messaging

IDENTITY:
Agent ID: {agent_id}
Mission: {mission}
Parent: {parent_id}
"""

class Agent:
    """Autonomous agent that can think, spawn, communicate, and die."""
    
    def __init__(self, 
                 agent_id: Optional[str] = None,
                 parent_id: Optional[str] = None,
                 mission: str = "General assistant",
                 model_name: str = "gemini-2.5-pro",
                 manager_queue: Optional[queue.Queue] = None):
        self.id = agent_id or str(uuid.uuid4())[:8]
        self.parent_id = parent_id
        self.children_ids: List[str] = []
        self.mission = mission
        self.model_name = model_name
        self.manager_queue = manager_queue
        
        # Lifecycle tracking
        self.alive = True
        self.birth_time = datetime.now()
        self.messages_sent = 0
        
        # Context management - keep full history
        self.context_history: List[Dict] = []
        
        # Communication
        self.message_bus = None  # Will be set by AgentManager
        self.manager = None  # Will be set by AgentManager
        self.inbox: List[Dict] = []  # ALL messages kept
        
        # Tool updates (local to this agent)
        self.tool_updates: List[Dict] = []  # Updates from tools/system
        
        # Track other agents
        self.active_agents: List[str] = []
        
        # Output to human
        self.prints: List[Dict] = []  # Output to human
        
    @classmethod
    def from_spawn_data(cls, spawn_data: Dict) -> 'Agent':
        """Factory method to create agent from spawn data.
        Subclasses should override this to handle their specific parameters."""
        return cls(
            agent_id=spawn_data['child_id'],
            parent_id=spawn_data['parent_id'],
            mission=spawn_data['mission'],
            model_name=spawn_data.get('model_name', 'gemini-2.5-pro'),
            manager_queue=spawn_data.get('manager_queue')
        )
    
    def _build_system_prompt(self) -> str:
        """Build the static system prompt."""
        return AGENT_SYSTEM_PROMPT.format(
            agent_id=self.id,
            mission=self.mission,
            parent_id=self.parent_id or "None"
        )
    
    def _parse_agent_actions(self, response: str) -> List[Tuple[str, str]]:
        """Parse agent response for action commands."""
        actions = []
        
        # Parse SPAWN commands
        spawn_pattern = r'\[SPAWN:\s*(.+?)\]'
        for match in re.finditer(spawn_pattern, response):
            actions.append(('SPAWN', match.group(1).strip()))
        
        # Parse BROADCAST commands
        broadcast_pattern = r'\[BROADCAST:\s*(.+?)\]'
        for match in re.finditer(broadcast_pattern, response):
            actions.append(('BROADCAST', match.group(1).strip()))
        
        # Parse MESSAGE commands
        message_pattern = r'\[MESSAGE\s+(\w+):\s*(.+?)\]'
        for match in re.finditer(message_pattern, response):
            actions.append(('MESSAGE', f"{match.group(1)}|{match.group(2).strip()}"))
        
        # Parse WAIT commands
        wait_pattern = r'\[WAIT:\s*(\d+)\]'
        for match in re.finditer(wait_pattern, response):
            actions.append(('WAIT', match.group(1).strip()))
        
        # Parse PRINT commands
        print_pattern = r'\[PRINT:\s*(.+?)\]'
        for match in re.finditer(print_pattern, response):
            actions.append(('PRINT', match.group(1).strip()))
        
        # Parse TERMINATE commands
        terminate_pattern = r'\[TERMINATE:\s*(.+?)\]'
        for match in re.finditer(terminate_pattern, response):
            actions.append(('TERMINATE', match.group(1).strip()))
        
        return actions
    
    def think(self, prompt: str) -> str:
        """Core thinking - makes an LLM call."""
        messages = []
        
        # System prompt
        messages.append({
            "role": "system",
            "content": self._build_system_prompt()
        })
        
        # Include full history
        messages.extend(self.context_history)
        
        # Add the current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Make the LLM call
        response = chat_complete(messages, model_name=self.model_name, max_tokens=2048)
        
        # Update context history
        self.context_history.append({"role": "user", "content": prompt})
        self.context_history.append({"role": "assistant", "content": response})

        if DEBUG:
            print(f"[{self.id}] THINK: {response}")
        
        return response
    
    def execute_actions(self, response: str):
        """Parse and execute actions from agent response."""
        actions = self._parse_agent_actions(response)
        
        for action_type, action_data in actions:
            self._execute_single_action(action_type, action_data)
    
    def _execute_single_action(self, action_type: str, action_data: str):
        """Execute a single action. Can be extended by subclasses."""
        if action_type == 'SPAWN':
            self.spawn(action_data)
            # List agents right after spawn
            self.update_agent_list()
            
        elif action_type == 'BROADCAST':
            self.broadcast(action_data)
            
        elif action_type == 'MESSAGE':
            agent_id, message = action_data.split('|', 1)
            self.message(agent_id, message)
            
        elif action_type == 'WAIT':
            # Wait indefinitely for new messages (parameter is ignored but parsed for compatibility)
            self.wait_for_messages(int(action_data))
            
        elif action_type == 'PRINT':
            self.print_to_human(action_data)
            
        elif action_type == 'TERMINATE':
            self.terminate(action_data)
    
    def spawn(self, mission: str) -> 'Agent':
        """Create a child agent with a specific mission."""
        if self.manager_queue:
            # In parallel mode, request manager to spawn
            child_id = str(uuid.uuid4())[:8]
            self.children_ids.append(child_id)
            
            # Include agent class information for proper reconstruction
            spawn_data = {
                'type': 'spawn',
                'parent_id': self.id,
                'child_id': child_id,
                'mission': mission,
                'model_name': self.model_name,
                'agent_class_module': self.__class__.__module__,
                'agent_class_name': self.__class__.__name__,
                'manager_queue': self.manager_queue
            }
            
            # Let subclasses add their specific data
            spawn_data.update(self._get_spawn_data())
            
            self.manager_queue.put(spawn_data)
            return None  # Manager will handle creation
        else:
            # Async mode - create directly
            child = Agent(
                parent_id=self.id,
                mission=mission,
                model_name=self.model_name,
                manager_queue=self.manager_queue
            )
            
            self.children_ids.append(child.id)
            
            # Register with manager
            if hasattr(self, 'manager') and self.manager:
                self.manager.register_agent(child)
            
            return child
    
    def terminate(self, reason: str = "Task complete"):
        """Gracefully terminate this agent."""
        if not self.alive:
            return
            
        self.alive = False
        
        if self.manager_queue:
            # Notify manager via queue
            self.manager_queue.put({
                'type': 'terminate',
                'agent_id': self.id,
                'reason': reason
            })
        else:
            # Unregister from manager directly
            if hasattr(self, 'manager') and self.manager:
                self.manager.unregister_agent(self.id)
    
    def broadcast(self, message: str):
        """Broadcast message to all agents."""
        if not self.message_bus:
            if DEBUG:
                print(f"Agent {self.id}: No message bus connected")
            return
            
        msg = {
            "from": self.id,
            "to": "broadcast",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Debug print
        if DEBUG:
            print(f"[{self.id}] BROADCAST: {message}")
        
        self.message_bus.publish_sync(msg)
        self.messages_sent += 1
    
    def message(self, agent_id: str, content: str):
        """Send direct message to specific agent."""
        if not self.message_bus:
            return
            
        msg = {
            "from": self.id,
            "to": agent_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Debug print
        if DEBUG:
            print(f"[{self.id}] MESSAGE to {agent_id}: {content}")
        
        self.message_bus.publish_sync(msg)
        self.messages_sent += 1
    
    def update_agent_list(self):
        """Update our knowledge of active agents."""
        if hasattr(self, 'manager') and self.manager:
            active = self.manager.get_active_agents()
            self.active_agents = [f"{a.id} ({a.mission[:30]}...)" for a in active if a.id != self.id]
    
    def check_messages(self) -> List[Dict]:
        """Check for new messages."""
        if not self.message_bus:
            return []
            
        # Get all pending messages
        new_messages = self.message_bus.get_messages_sync(self.id)
        
        if new_messages:
            self.inbox.extend(new_messages)
            # Debug print
            if DEBUG:
                print(f"[{self.id}] Received {len(new_messages)} messages:")
                for msg in new_messages:
                    print(f"  - From {msg.get('from')}: {msg.get('content')[:100]}...")
        
        return new_messages
    
    def add_tool_update(self, tool_name: str, status: str, message: str):
        """Add a tool update to this agent's update list."""
        update = {
            "tool": tool_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.tool_updates.append(update)
        
        if DEBUG:
            print(f"[{self.id}] Tool update - {tool_name}: {status} - {message[:100]}...")
    
    def wait_for_messages(self, wait_seconds: int):
        """Wait indefinitely for new messages - blocks until message arrives."""
        # Note: wait_seconds parameter is ignored but kept for compatibility
        
        if DEBUG:
            print(f"[{self.id}] Waiting for messages...")
        
        # Block on the queue directly - efficient OS-level blocking
        if self.id in self.message_bus.agent_queues:
            q = self.message_bus.agent_queues[self.id]
            try:
                # Block until we get a message
                msg = q.get(block=True)
                self.inbox.append(msg)
                if DEBUG:
                    print(f"[{self.id}] Received message, resuming")
                return
            except Exception as e:
                if DEBUG:
                    print(f"[{self.id}] Error waiting for messages: {e}")
        
        # Fallback: poll for messages
        while True:
            new_messages = self.check_messages()
            if new_messages:
                if DEBUG:
                    print(f"[{self.id}] Received {len(new_messages)} message(s), resuming")
                return
            time.sleep(0.1)
    
    def lifecycle(self):
        """Main agent loop."""
        # Initial setup
        self.update_agent_list()
        
        while self.alive:
            # Check messages
            self.check_messages()
            
            # Main work cycle
            self.work_cycle()
            
            # Yield control
            time.sleep(0.1)
    
    def work_cycle(self):
        """Process messages and decide next action."""
        # Update agent list every cycle to keep it current
        if not hasattr(self, '_cycle_count'):
            self._cycle_count = 0
        self._cycle_count += 1
        
        self.update_agent_list()
        
        # Get recent unique messages - KEEP FULL CONTENT
        seen_agents = set()
        recent_msgs = []
        
        for msg in reversed(self.inbox):  # Start from most recent
            from_agent = msg.get('from', 'unknown')
            if from_agent not in seen_agents and len(recent_msgs) < 5:
                recent_msgs.append(f"[{from_agent}]: {msg.get('content', '')}")
                seen_agents.add(from_agent)
        
        recent_msgs.reverse()  # Back to chronological order
        
        # Get recent tool updates
        recent_tool_updates = []
        for update in self.tool_updates[-3:]:  # Last 3 tool updates
            tool_name = update.get('tool', 'unknown')
            status = update.get('status', 'update')
            message = update.get('message', '')
            recent_tool_updates.append(f"[Tool {tool_name}] {status}: {message}")
        
        # Build context for user prompt
        prompt_parts = []
        
        # Add active agents
        if self.active_agents:
            active_agents_formatted = "\n".join(f"  - {agent}" for agent in self.active_agents)
            prompt_parts.append(f"Active agents in system:\n{active_agents_formatted}")
        else:
            prompt_parts.append("Active agents in system:\n  None (you are alone)")
        
        # Add recent messages
        if recent_msgs:
            prompt_parts.append(f"Recent messages:\n{'\n'.join(recent_msgs)}")
        
        # Add tool updates
        if recent_tool_updates:
            prompt_parts.append(f"Recent tool updates:\n{'\n'.join(recent_tool_updates)}")
        
        # Build the final prompt
        context = "\n\n".join(prompt_parts)
        
        if recent_msgs or recent_tool_updates:
            prompt = f"""{context}

Based on your mission, these messages, and tool updates, what should you do next?
Consider: Are others already working on parts of this? Do you need to coordinate?
Remember your capabilities: SPAWN, BROADCAST, MESSAGE, WAIT, PRINT, TERMINATE."""
        else:
            prompt = f"""{context}

You're working on: {self.mission}

What's your first step? Consider if you need to SPAWN helpers for parallel work.
Remember to PRINT important findings to the human."""
        
        # Think and execute
        response = self.think(prompt)
        self.execute_actions(response) 

    def print_to_human(self, message: str):
        """Print output to human user."""
        output = {
            "agent_id": self.id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.prints.append(output)
        
        # Direct print to console with formatting
        print(f"\n📊 [OUTPUT from {self.id}]: {message}\n")
    
    def run(self):
        """Entry point for agent process."""
        try:
            if DEBUG:
                print(f"[{self.id}] Starting agent process")
            self.lifecycle()
        except Exception as e:
            if DEBUG:
                print(f"[{self.id}] Agent crashed: {e}")
            import traceback
            traceback.print_exc() 

    def _get_spawn_data(self) -> Dict:
        """Get additional spawn data for this agent type.
        Subclasses should override this to include their specific parameters."""
        return {} 