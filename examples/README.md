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

## Tool Integration Example

Shows how to extend agents with custom tools:

```bash
cd examples
python tool_example.py
```

This demonstrates:
1. Defining custom Python functions as tools
2. Writing tool documentation for the system prompt
3. Creating tool-enabled agents
4. Agents using tools to complete tasks

The example includes:
- `calculate()` - A math expression evaluator
- `get_time()` - Returns current timestamp

The agent will use its built-in capabilities (SPAWN, BROADCAST, MESSAGE, WAIT, TERMINATE) plus the custom tools to complete the task. 