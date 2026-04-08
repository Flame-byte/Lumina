# Lumina

An agent system designed for small local models, enabling stable and efficient execution of agent tasks.

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

## License

MIT
