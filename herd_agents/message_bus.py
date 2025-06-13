import asyncio
import os
from typing import Dict, List
from collections import defaultdict
from datetime import datetime

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

class MessageBus:
    """Simple async message bus for agent communication."""
    
    def __init__(self):
        # Messages queue for each agent
        self.agent_queues: Dict[str, asyncio.Queue] = {}
        
        # Global message history (limited)
        self.message_history: List[Dict] = []
        self.max_history = 1000
        
    def register_agent(self, agent_id: str):
        """Register a new agent with the message bus."""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.Queue()
    
    def unregister_agent(self, agent_id: str):
        """Remove agent from message bus."""
        if agent_id in self.agent_queues:
            del self.agent_queues[agent_id]
    
    async def publish(self, message: Dict):
        """Publish a message to the bus."""
        # Add to history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Route message
        to = message.get('to', 'broadcast')
        from_agent = message.get('from')
        
        if to == 'broadcast':
            # Send to all agents except sender
            for agent_id in self.agent_queues:
                if agent_id != from_agent:
                    await self._deliver_to_agent(agent_id, message)
        else:
            # Direct message - check if delivery succeeds
            delivered = await self._deliver_to_agent(to, message)
            
            # If delivery failed and sender exists, notify them
            if not delivered and from_agent and from_agent in self.agent_queues:
                if DEBUG:
                    print(f"[MessageBus] Delivery failed: {from_agent} -> {to} (agent not found)")
                
                failure_notice = {
                    "from": "system",
                    "to": from_agent,
                    "content": f"DELIVERY FAILED: Agent {to} is not active. Your message was not delivered.",
                    "timestamp": datetime.now().isoformat(),
                    "failed_message": message.get("content", "")[:100] + "..."
                }
                # Deliver failure notice directly without adding to history
                await self._deliver_to_agent(from_agent, failure_notice)
    
    async def _deliver_to_agent(self, agent_id: str, message: Dict) -> bool:
        """Deliver message to specific agent's queue. Returns True if delivered."""
        if agent_id in self.agent_queues:
            # Non-blocking put
            self.agent_queues[agent_id].put_nowait(message)
            return True
        return False
    
    async def get_messages(self, agent_id: str) -> List[Dict]:
        """Get all pending messages for an agent (non-blocking)."""
        if agent_id not in self.agent_queues:
            return []
        
        messages = []
        queue = self.agent_queues[agent_id]
        
        # Get all messages currently in queue
        while not queue.empty():
            messages.append(queue.get_nowait())
        
        return messages
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get message history."""
        return self.message_history[-limit:] 