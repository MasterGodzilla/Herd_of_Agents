import asyncio
import uuid
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from api import chat_complete
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Detailed system prompt that explains all agent capabilities
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

4. WAIT - Pause before continuing
   Format: [WAIT: <seconds>]
   Example: [WAIT: 2]
   Use when: Need to give others time to respond, pace your work

5. TERMINATE - End your existence
   Format: [TERMINATE: <reason>]
   Example: [TERMINATE: Task complete, findings shared]
   Use when: Work is done, you're redundant, or reached dead end

IMPORTANT RULES:
- Be concise (tokens are expensive)
- Spawn agents when you identify parallel work
- Terminate when your specific task is complete
- Check the active agents list before messaging

CURRENT IDENTITY:
Agent ID: {agent_id}
Mission: {mission}
Parent: {parent_id}
Context: {working_memory}

ACTIVE AGENTS IN SYSTEM:
{active_agents}

RECENT MESSAGES FOR YOU:
{recent_messages}
"""

class Agent:
    """Basic autonomous agent that can think, spawn, communicate, and die."""
    
    def __init__(self, 
                 agent_id: Optional[str] = None,
                 parent_id: Optional[str] = None,
                 mission: str = "General assistant",
                 model_name: str = "gemini-2.5-flash"):
        self.id = agent_id or str(uuid.uuid4())[:8]
        self.parent_id = parent_id
        self.children_ids: List[str] = []
        self.mission = mission
        self.model_name = model_name
        
        # Lifecycle tracking
        self.alive = True
        self.birth_time = datetime.now()
        self.messages_sent = 0
        
        # Context management - keep full history
        self.context_history: List[Dict] = []
        self.working_memory: str = ""  # Will be filled by manager
        
        # Communication
        self.message_bus = None  # Will be set by AgentManager
        self.inbox: List[Dict] = []  # ALL messages kept
        
        # Track other agents
        self.active_agents: List[str] = []
        
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current agent state."""
        # Get recent messages - show full content
        recent_messages = []
        for msg in self.inbox[-10:]:  # Last 10 messages
            recent_messages.append(f"[{msg.get('from', 'unknown')}]: {msg.get('content', '')}")
        
        # Format active agents list nicely
        if self.active_agents:
            active_agents_formatted = "\n".join(f"  - {agent}" for agent in self.active_agents)
        else:
            active_agents_formatted = "  None (you are alone)"
        
        return AGENT_SYSTEM_PROMPT.format(
            agent_id=self.id,
            mission=self.mission,
            parent_id=self.parent_id or "None",
            working_memory=self.working_memory,
            active_agents=active_agents_formatted,
            recent_messages="\n".join(recent_messages) if recent_messages else "No messages yet"
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
        
        # Parse TERMINATE commands
        terminate_pattern = r'\[TERMINATE:\s*(.+?)\]'
        for match in re.finditer(terminate_pattern, response):
            actions.append(('TERMINATE', match.group(1).strip()))
        
        return actions
    
    async def think(self, prompt: str) -> str:
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

        
        
        return response
    
    async def execute_actions(self, response: str):
        """Parse and execute actions from agent response."""
        actions = self._parse_agent_actions(response)
        
        for action_type, action_data in actions:
            if action_type == 'SPAWN':
                await self.spawn(action_data)
                # List agents right after spawn
                await self.update_agent_list()
                
            elif action_type == 'BROADCAST':
                await self.broadcast(action_data)
                
            elif action_type == 'MESSAGE':
                agent_id, message = action_data.split('|', 1)
                await self.message(agent_id, message)
                
            elif action_type == 'WAIT':
                await asyncio.sleep(int(action_data))
                
            elif action_type == 'TERMINATE':
                await self.terminate(action_data)
    
    async def spawn(self, mission: str) -> 'Agent':
        """Create a child agent with a specific mission."""
        child = Agent(
            parent_id=self.id,
            mission=mission,
            model_name=self.model_name
        )
        
        self.children_ids.append(child.id)
        
        # Register with manager
        if hasattr(self, 'manager') and self.manager:
            await self.manager.register_agent(child)
        
        return child
    
    async def terminate(self, reason: str = "Task complete"):
        """Gracefully terminate this agent."""
        if not self.alive:
            return
            
        self.alive = False
        
        # Unregister from manager
        if hasattr(self, 'manager') and self.manager:
            await self.manager.unregister_agent(self.id)
    
    async def broadcast(self, message: str):
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
        
        await self.message_bus.publish(msg)
        self.messages_sent += 1
    
    async def message(self, agent_id: str, content: str):
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
        
        await self.message_bus.publish(msg)
        self.messages_sent += 1
    
    async def update_agent_list(self):
        """Update our knowledge of active agents."""
        if hasattr(self, 'manager') and self.manager:
            active = self.manager.get_active_agents()
            self.active_agents = [f"{a.id} ({a.mission[:30]}...)" for a in active if a.id != self.id]
    
    async def check_messages(self) -> List[Dict]:
        """Check for new messages."""
        if not self.message_bus:
            return []
            
        # Get all pending messages
        new_messages = await self.message_bus.get_messages(self.id)
        
        if new_messages:
            self.inbox.extend(new_messages)
            # Debug print
            if DEBUG:
                print(f"[{self.id}] Received {len(new_messages)} messages:")
                for msg in new_messages:
                    print(f"  - From {msg.get('from')}: {msg.get('content')[:100]}...")
        
        return new_messages
    
    async def lifecycle(self):
        """Main agent loop."""
        # Initial setup
        await self.update_agent_list()
        if hasattr(self, 'manager') and self.manager:
            self.working_memory = await self.manager.get_agent_summary(self.id)
        
        while self.alive:
            # Check messages
            await self.check_messages()
            
            # Main work cycle
            await self.work_cycle()
            
            # Update summary periodically
            if hasattr(self, '_cycle_count') and self._cycle_count % 5 == 0:
                if hasattr(self, 'manager') and self.manager:
                    await self.manager.update_agent_summary(self.id)
                    self.working_memory = await self.manager.get_agent_summary(self.id)
            
            # Yield control
            await asyncio.sleep(0.1)
    
    async def work_cycle(self):
        """Process messages and decide next action."""
        # Update agent list every cycle to keep it current
        if not hasattr(self, '_cycle_count'):
            self._cycle_count = 0
        self._cycle_count += 1
        
        await self.update_agent_list()
        
        # Get recent unique messages - KEEP FULL CONTENT
        seen_agents = set()
        recent_msgs = []
        
        for msg in reversed(self.inbox):  # Start from most recent
            from_agent = msg.get('from', 'unknown')
            if from_agent not in seen_agents and len(recent_msgs) < 5:
                recent_msgs.append(f"[{from_agent}]: {msg.get('content', '')}")
                seen_agents.add(from_agent)
        
        recent_msgs.reverse()  # Back to chronological order
        
        # Build prompt
        if recent_msgs:
            prompt = f"""Recent messages:
{"\n".join(recent_msgs)}

Based on your mission and these messages, what should you do next?
Consider: Are others already working on parts of this? Do you need to coordinate?
Remember your capabilities: SPAWN, BROADCAST, MESSAGE, WAIT, TERMINATE."""
        else:
            # No messages, focus on mission
            prompt = f"""You're working on: {self.mission}

What's your first step? Consider if you need to SPAWN helpers for parallel work."""
        
        # Think and execute
        response = await self.think(prompt)
        await self.execute_actions(response) 