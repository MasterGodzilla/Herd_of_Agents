import os
from typing import Dict, List, Optional
from datetime import datetime
import threading
import queue

# DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DEBUG=True

class MessageBus:
    """Message bus for parallel agent communication using threading queues."""
    
    def __init__(self):
        """
        Initialize message bus for parallel execution.
        
        No need for mp.Manager anymore with threading.
        """
        self.agent_queues: Dict[str, queue.Queue] = {}
        self.message_history = []
        self.lock = threading.Lock()
        self.max_history = 1000
    
    def register_agent(self, agent_id: str):
        """Register a new agent with the message bus."""
        with self.lock:
            if agent_id not in self.agent_queues:
                self.agent_queues[agent_id] = queue.Queue()
                if DEBUG:
                    print(f"[MessageBus] Registered agent {agent_id}")
    
    def unregister_agent(self, agent_id: str):
        """Remove agent from message bus."""
        with self.lock:
            if agent_id in self.agent_queues:
                # Clear queue first
                q = self.agent_queues[agent_id]
                while not q.empty():
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break
                del self.agent_queues[agent_id]
                if DEBUG:
                    print(f"[MessageBus] Unregistered agent {agent_id}")
    
    def publish(self, message: Dict):
        """Publish a message to the bus."""
        with self.lock:
            # Add to history
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)
        
        # Route message
        to = message.get('to', 'broadcast')
        from_agent = message.get('from')
        
        if to == 'broadcast':
            # Send to all agents except sender
            with self.lock:
                agent_ids = list(self.agent_queues.keys())
                
            for agent_id in agent_ids:
                if agent_id != from_agent:
                    self._deliver_to_agent(agent_id, message)
        else:
            # Direct message
            delivered = self._deliver_to_agent(to, message)
            
            # If delivery failed, notify sender
            if not delivered and from_agent:
                if DEBUG:
                    print(f"[MessageBus] Delivery failed: {from_agent} -> {to} (agent not found)")
                    
                failure_notice = {
                    "from": "system",
                    "to": from_agent,
                    "content": f"DELIVERY FAILED: Agent {to} is not active.",
                    "timestamp": datetime.now().isoformat()
                }
                self._deliver_to_agent(from_agent, failure_notice)
    
    def publish_sync(self, message: Dict):
        """Alias for publish() for backward compatibility."""
        return self.publish(message)
    
    def _deliver_to_agent(self, agent_id: str, message: Dict) -> bool:
        """Deliver message to specific agent's queue."""
        with self.lock:
            if agent_id in self.agent_queues:
                try:
                    self.agent_queues[agent_id].put_nowait(message)
                    return True
                except queue.Full:
                    if DEBUG:
                        print(f"[MessageBus] Queue full for {agent_id}")
                    return False
        return False
    
    def get_messages(self, agent_id: str) -> List[Dict]:
        """Get all pending messages for an agent."""
        messages = []
        
        with self.lock:
            if agent_id not in self.agent_queues:
                return messages
            q = self.agent_queues[agent_id]
        
        # Get messages without holding lock
        while True:
            try:
                msg = q.get_nowait()
                messages.append(msg)
            except queue.Empty:
                break
        
        return messages
    
    def get_messages_sync(self, agent_id: str) -> List[Dict]:
        """Alias for get_messages() for backward compatibility."""
        return self.get_messages(agent_id)
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get message history."""
        with self.lock:
            return list(self.message_history[-limit:]) 