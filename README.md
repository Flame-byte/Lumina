# Lumina Agent

A dual-agent (Planner + Executor) collaboration system built on LangGraph, featuring Human-in-the-loop (HITL) confirmation flow.

## Features

- **Dual-Agent Architecture**: Separation of Planner (planning) and Executor (execution)
- **HITL Support**: Users can confirm or modify plans at critical checkpoints
- **State Persistence**: SQLite checkpoint storage for session state
- **Extensible Tools**: LangChain-based extensible tool system
- **Multi-Modal Support**: Text, image, PDF, and Excel file processing via preprocessing module
- **Context Compression**: Automatic compression of conversation history to prevent token overflow
- **Local Deployment**: Supports Ollama and other local models for privacy control

## Project Structure

```
Lumina_Agent_EN/
├── agent/                      # Agent core code
│   ├── state.py                # AgentState definition
│   ├── planner.py              # Planner agent
│   ├── executor.py             # Executor agent
│   └── graph.py                # LangGraph state graph
├── tools/                      # Tool system
│   ├── registry.py             # Tool registry
│   ├── base.py                 # Tool base class
│   └── *.py                    # Tool implementations
├── preprocessing/              # File preprocessing module
├── config/                     # Configuration files
│   ├── llm_config.yaml         # LLM configuration
│   ├── agent_config.yaml       # Agent configuration
│   └── prompts/                # Prompt templates
│       ├── planner.yaml        # Planner prompts
│       └── executor.yaml       # Executor prompts
├── api/                        # FastAPI backend
│   ├── routes.py               # API routes
│   └── schemas.py              # Pydantic models
├── database/                   # Database layer (SQLite)
├── services/                   # Business services
├── tests/                      # Test code
├── agent-chat-ui/              # Next.js frontend
├── main.py                     # Application entry point
├── requirements.txt            # Dependencies
└── project_design.md           # Design documentation
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure LLM

Edit `config/llm_config.yaml`:

```yaml
default:
  provider: deepseek
  model: deepseek-chat
  base_url: https://api.deepseek.com
  api_key: sk-your-api-key-here
```

### 3. Start the Service

```bash
python main.py
```

The service will start at `http://localhost:8000`.

### 4. API Documentation

Visit `http://localhost:8000/docs` for Swagger API documentation.

## Architecture

### Dual-Agent State Flow

```
START → planner → [HITL Interrupt - Awaiting Confirmation]
                    ├─ Approve → executor_agent ↔ executor_tools → executor_final → END
                    └─ Reject → planner (re-planning)
```

### Message Storage Strategy

1. **Runtime**: Messages stored in `AgentState.planner_messages` (LangGraph checkpoint)
2. **Persistence**: Async sync to SQLite database (`sessions/{session_id}/session.db`)
3. **Recovery**: When user switches sessions, messages are restored from database to checkpoint

## API Usage

### Start a Conversation

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Read this file for me",
    "files": ["path/to/file.txt"]
  }'
```

### Approve Plan

```bash
curl -X POST http://localhost:8000/api/confirm \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "your-thread-id"}'
```

### Reject Plan

```bash
curl -X POST http://localhost:8000/api/reject \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "your-thread-id",
    "feedback": "Please adjust the task order"
  }'
```

### Check Status

```bash
curl http://localhost:8000/api/status/your-thread-id
```

## Adding New Tools

1. Inherit from `LuminaTool` base class:

```python
from tools.base import LuminaTool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    param: str = Field(description="Parameter description")

class MyTool(LuminaTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "My tool description"

    def get_input_schema(self) -> type[BaseModel]:
        return MyToolInput

    def execute(self, **kwargs) -> dict:
        # Implement tool logic
        return {"result": "success"}
```

2. Register in `main.py`:

```python
from tools.my_tool import MyTool

registry.register(
    tool=MyTool().build(),
    category="custom",
    tags=["custom"]
)
```

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

## Configuration

### LLM Configuration (`config/llm_config.yaml`)

- `default`: Default configuration
- `planner`: Planner-specific configuration (temperature=0.7, more creative)
- `executor`: Executor-specific configuration (temperature=0.3, more precise)

### Agent Configuration (`config/agent_config.yaml`)

- `session.checkpoint_path`: SQLite checkpoint file path
- `planner.hitl_enabled`: Enable/disable HITL
- `executor.max_retries`: Maximum tool execution retries

### Prompt Configuration (`config/prompts/`)

- `planner.yaml`: Planner system prompts, re-planning feedback templates, file content templates
- `executor.yaml`: Executor system prompts, task instruction templates, retry prompts

Customize prompts by modifying the corresponding YAML files without touching the code.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | LangGraph + LangChain |
| Language | Python 3.12 |
| Database | SQLite (langgraph-checkpoint-sqlite) |
| Backend | FastAPI |
| Frontend | Next.js / React / TypeScript |
| Models | DeepSeek / Ollama |

## License

MIT
