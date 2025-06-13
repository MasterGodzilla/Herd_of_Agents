# Herd of Agents

A self-organizing multi-agent system where LLM agents dynamically spawn, communicate, and collaborate without predefined roles. **Now fully parallelized using threading for maximum performance.**

## Core Concepts

- **No predefined roles** - Agents specialize through experience
- **Dynamic spawning** - Agents create children when they identify parallel work
- **Emergent collaboration** - Agents self-organize based on the task
- **Parallel execution** - Each agent runs in its own thread for true parallelism
- **Thread-safe communication** - Lock-protected message passing between agents
- **Automatic summarization** - Manager maintains summaries to prevent repetition

## Architecture

### Threading-Based Parallel System

**Performance Optimized:** The system now uses Python threading for parallel agent execution:
- Each agent runs in its own daemon thread
- Thread-safe message queues for inter-agent communication
- Blocking queue operations for efficient message waiting
- No async/await overhead - pure threading performance

### Agent Capabilities

Agents can:
1. **SPAWN** - Create child agents for subtasks (spawned in new threads)
2. **BROADCAST** - Send messages to all agents (thread-safe delivery)
3. **MESSAGE** - Direct message specific agents (queue-based routing)
4. **WAIT** - Pause execution (efficient OS-level blocking on queues)
5. **PRINT** - Send output directly to human user (console)
6. **TERMINATE** - End their existence (thread cleanup)

### Key Components

- `agent.py` - Thread-based agent class with LLM-powered decision making
- `message_bus.py` - Thread-safe pub/sub using queues and locks
- `manager.py` - Thread lifecycle management and agent coordination
- `api.py` - Unified interface for multiple LLM providers

## Installation & Usage

### Installation

```bash
# Install the package in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Quick Start

```python
# Using the threading-based package
import time
from herd_agents import AgentManager

def main():
    manager = AgentManager()
    agent = manager.create_genesis_agent(
        mission="Spawn two agents, tell them to say hello to each other, and report back their mood for the day."
    )
    manager.start()
    manager.wait_for_convergence(timeout=30)
    manager.stop()

if __name__ == "__main__":
    main()
```

### Simple Example

```bash
# Run the simple example
python examples/tool_example.py
```

## Key Design Principles

- **Threading-based** - Pure threading architecture for performance
- **Autonomous** - Agents make independent decisions and self-organize
- **Emergent** - System behavior arises naturally from agent interactions
- **Thread-safe** - Lock-protected communication and shared state

## Current Status (v0.2 - Threading Edition)

**Core Features Working:**
- Thread-based parallel execution with message passing
- Dynamic agent spawning and termination
- Manager-maintained summaries and coordination
- Interactive debugging and monitoring

## TODO:
- Abstract out a tool class to standardize tool usage
- Tool Library (user can pick and choose existing tools)

### API Keys Required:
Set environment variables for LLM providers you want to use:
- `GOOGLE_API_KEY` for Gemini
- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Claude

## Testing

```bash
# Basic test
python test_basic.py

# Interactive mode (recommended)
python interactive.py
```
The interactive mode shows all agent communications in real-time and provides a good understanding of how agents collaborate.

