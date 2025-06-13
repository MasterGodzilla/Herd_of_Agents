# Herd of Agents

A self-organizing multi-agent system where LLM agents dynamically spawn, communicate, and collaborate without predefined roles.

## Core Concepts

- **No predefined roles** - Agents specialize through experience
- **Dynamic spawning** - Agents create children when they identify parallel work
- **Emergent collaboration** - Agents self-organize based on the task
- **Async message passing** - Non-blocking communication between agents
- **Automatic summarization** - Manager maintains summaries to prevent repetition

## Architecture

### Agent Capabilities

Agents can:
1. **SPAWN** - Create child agents for subtasks
2. **BROADCAST** - Send messages to all agents  
3. **MESSAGE** - Direct message specific agents
4. **WAIT** - Pause execution
5. **LIST_AGENTS** - See who else is active
6. **TERMINATE** - End their existence

### Key Components

- `agent.py` - Basic agent class with LLM-powered decision making
- `message_bus.py` - Simple async pub/sub for agent communication
- `agent_manager.py` - Manages agent lifecycles and maintains summaries
- `api.py` - Unified interface for multiple LLM providers

## Usage

```python
# Run interactive mode (recommended for testing)
python interactive.py

# Or programmatically:
from agent_manager import AgentManager

manager = AgentManager()
genesis = await manager.create_genesis_agent(
    mission="Test spawning and communication"
)
await manager.start()
await manager.wait_for_convergence(timeout=60)
await manager.stop()
```

## Key Design Principles

1. **Agents keep full history** - No compression yet, full context preserved
2. **Manager handles summaries** - Centralized to avoid repetition
3. **Message accumulation** - Agents process message batches, not individual messages
4. **Natural termination** - Agents decide when their work is complete
5. **No orchestration** - System behavior emerges from agent interactions

## Current Status (v0.1)

### What's Working:
- Basic agent lifecycle (spawn, communicate, terminate)
- Message passing with timestamps
- Dynamic agent discovery (LIST_AGENTS)
- Manager-maintained summaries to prevent work duplication
- Debug mode (set DEBUG=true environment variable)
- Interactive terminal interface

### What's NOT Implemented Yet:
- Tool integration (web search, code execution, etc.)
- Work stealing between agents
- Persistence/checkpointing
- Context compression (agents keep full history)
- Advanced coordination patterns
- Force interruption mechanism

### Important Implementation Notes:

1. **Message Format**: All messages include `from`, `to`, `content`, and `timestamp`
2. **System Prompt**: Detailed prompt in `AGENT_SYSTEM_PROMPT` explains all capabilities
3. **Action Parsing**: Uses regex to parse [ACTION: data] format from LLM responses
4. **Summary System**: Manager calls separate LLM to summarize agent work periodically
5. **Debug Prints**: Enable with `DEBUG=true` to see all communications

### Known Behaviors:
- Agents will naturally spawn children when they identify parallel work
- Agents update their agent list after spawning (automatic LIST_AGENTS)
- Working memory is updated every 5 cycles from manager's summary
- Messages are shown to agents in batches (last 5 unique senders)
- Agents see full message content (no truncation in prompts)

### API Keys Required:
Set environment variables for LLM providers you want to use:
- `GOOGLE_API_KEY` for Gemini
- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Claude

## Next Steps

- Add tool integration (web search, etc)
- Implement work stealing for efficiency  
- Add persistence/checkpointing
- Scale testing with 100+ agents
- Implement context compression strategies
- Add force interruption mechanism
- Create specialized agent types through prompting

## Testing

```bash
# Basic test
python test_basic.py

# Interactive mode (recommended)
python interactive.py
```

The interactive mode shows all agent communications in real-time and provides a good understanding of how agents collaborate.
