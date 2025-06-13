# Herd of Agents Examples

## Simple Example

The most basic way to use the agent system:

```bash
cd examples
python simple_example.py
```

This will:
1. Create an agent manager
2. Spawn a single agent with a simple mission
3. Let the agent work for 30 seconds
4. Stop the system

## Tool Integration & Swarm Example

Shows the full power of the agent system with tools and multi-agent coordination:

```bash
cd examples
python tool_example.py
```

This comprehensive example demonstrates:

**Tool Integration:**
- Define custom Python functions as tools
- Tool documentation injected into system prompt
- Agents call tools with `[TOOL: tool_name(args)]`

**Multi-Agent Swarm:**
- Main agent spawns child agents for parallel work
- Each child handles part of the calculation
- Results communicated back and aggregated

**The Mission:**
Calculate sum of cubes (n³) for three ranges in parallel:
- Range 1-10: handled by child agent 1
- Range 11-20: handled by child agent 2  
- Range 21-30: handled by child agent 3
- Coordinator aggregates all results for grand total

**Available Tools:**
- `calculate()` - Math expression evaluator (supports sum, range, pow, etc.)
- `get_time()` - Returns current timestamp

Perfect for understanding how agents divide work, use tools, and coordinate! 