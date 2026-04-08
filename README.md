# Lumina

An agent system designed for small local models (such as Ollama), enabling them to execute agent tasks stably and efficiently.

## Quick Start

### Start Backend

```bash
pip install -r requirements.txt
python main.py
```

The backend will start at `http://localhost:8000`.

### Start Frontend

```bash
cd agent-chat-ui
pnpm install
pnpm dev
```

The frontend will start at `http://localhost:3000`.

## Configuration

### Configure LLM Model

Edit `config/llm_config.yaml`:

```yaml
default:
  provider: ollama  # or deepseek, openai, etc.
  model: qwen2.5:latest
  base_url: http://localhost:11434/v1
  api_key: ollama  # not required for local models
```

### Configure Agent

Edit `config/agent_config.yaml` for agent behavior settings.

### Configure Tools

Tools are defined in `tools/` directory. Edit `tools/config.yaml` to enable/disable tools.

## Hope you to know

This is just a naive version, only to verify if the framework works. I'm developing a smaller, faster version that can be installed directly. If you have any suggestions for this system, feel free to give me feedback. Thank you for your suggestions and attempts.

## License

MIT
