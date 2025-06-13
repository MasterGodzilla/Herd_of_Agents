"""Tool-enabled agent that supports custom tool integration."""

import re
from typing import Dict, List, Callable, Any, Optional
from .agent import Agent

class ToolAgent(Agent):
    """Agent with custom tool support."""
    
    def __init__(self, 
                 agent_id: Optional[str] = None,
                 parent_id: Optional[str] = None,
                 mission: str = "General assistant",
                 model_name: str = "gemini-2.5-flash",
                 tools: Optional[Dict[str, Callable]] = None,
                 tool_docs: Optional[str] = None):
        super().__init__(agent_id, parent_id, mission, model_name)
        
        # Tool management
        self.tools = tools or {}
        self.tool_docs = tool_docs or ""
        
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
    
    async def _execute_single_action(self, action_type: str, action_data: str):
        """Extend parent's action execution to handle tool calls."""
        if action_type == 'TOOL':
            # Execute tool
            tool_name, args_str = action_data.split('|', 1)
            await self.execute_tool(tool_name, args_str)
        else:
            # Let parent handle all other actions
            await super()._execute_single_action(action_type, action_data)
    
    async def execute_tool(self, tool_name: str, args_str: str):
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
    
    async def spawn(self, mission: str) -> 'ToolAgent':
        """Create a child agent with same tools."""
        child = ToolAgent(
            parent_id=self.id,
            mission=mission,
            model_name=self.model_name,
            tools=self.tools,  # Pass tools to children
            tool_docs=self.tool_docs
        )
        
        self.children_ids.append(child.id)
        
        # Register with manager
        if hasattr(self, 'manager') and self.manager:
            await self.manager.register_agent(child)
        
        return child 