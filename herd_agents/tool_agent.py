"""Tool-enabled agent that supports custom tool integration."""

import re
import uuid
from typing import Dict, List, Callable, Any, Optional
from .agent import Agent
import queue

class ToolAgent(Agent):
    """Agent with custom tool support."""
    
    def __init__(self, 
                 agent_id: Optional[str] = None,
                 parent_id: Optional[str] = None,
                 mission: str = "General assistant",
                 model_name: str = "gemini-2.5-flash",
                 manager_queue: Optional[queue.Queue] = None,
                 tools: Optional[Dict[str, Callable]] = None,
                 tool_docs: Optional[str] = None):
        super().__init__(agent_id, parent_id, mission, model_name, manager_queue)
        
        # Tool management
        self.tools = tools or {}
        self.tool_docs = tool_docs or ""
        
    @classmethod
    def from_spawn_data(cls, spawn_data: Dict) -> 'ToolAgent':
        """Create ToolAgent from spawn data."""
        return cls(
            agent_id=spawn_data['child_id'],
            parent_id=spawn_data['parent_id'],
            mission=spawn_data['mission'],
            model_name=spawn_data.get('model_name', 'gemini-2.5-flash'),
            manager_queue=spawn_data.get('manager_queue'),
            tools=spawn_data.get('tools', {}),
            tool_docs=spawn_data.get('tool_docs', '')
        )
    
    def _get_spawn_data(self) -> Dict:
        """Include tools in spawn data."""
        return {
            'tools': self.tools,
            'tool_docs': self.tool_docs
        }
        
    def _build_system_prompt(self) -> str:
        """Build system prompt with tool documentation."""
        base_prompt = super()._build_system_prompt()
        
        if self.tools and self.tool_docs:
            # Add tool documentation
            tool_section = f"""

CUSTOM TOOLS AVAILABLE:

{self.tool_docs}

To use a tool, format: [TOOL: <tool_name>(<args>)]
Example: [TOOL: calculate(2 + 2)]
"""
            return base_prompt + tool_section
        
        return base_prompt
    
    def _parse_agent_actions(self, response: str) -> List[tuple[str, str]]:
        """Parse agent response for actions including tool calls."""
        # Get base actions first
        actions = super()._parse_agent_actions(response)
        
        # Parse TOOL commands
        tool_pattern = r'\[TOOL:\s*(\w+)\((.*?)\)\]'
        for match in re.finditer(tool_pattern, response):
            tool_name = match.group(1).strip()
            args = match.group(2).strip()
            actions.append(('TOOL', f"{tool_name}|{args}"))
        
        return actions
    
    def _execute_single_action(self, action_type: str, action_data: str):
        """Extend parent's action execution to handle tool calls."""
        if action_type == 'TOOL':
            # Execute tool
            tool_name, args_str = action_data.split('|', 1)
            self.execute_tool(tool_name, args_str)
        else:
            # Let parent handle all other actions
            super()._execute_single_action(action_type, action_data)
    
    def execute_tool(self, tool_name: str, args_str: str):
        """Execute a tool and add result to context."""
        if tool_name not in self.tools:
            self.add_tool_update(tool_name, "error", f"Tool '{tool_name}' not found")
            return
        
        try:
            # Simple argument parsing (can be enhanced)
            # For now, just pass the string directly
            result = self.tools[tool_name](args_str)
            
            # Add tool result to updates
            self.add_tool_update(tool_name, "success", f"Result: {result}")
            
        except Exception as e:
            self.add_tool_update(tool_name, "error", f"Error: {str(e)}")
    
 