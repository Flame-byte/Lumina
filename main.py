"""
Lumina Agent - Main Entry Point

Dual-agent (Planner + Executor) collaboration system based on LangGraph
Supports HITL (Human-in-the-loop) confirmation workflow
"""

import yaml
import os
from pathlib import Path

from langchain_openai import ChatOpenAI

from tools.registry import ToolRegistry
from tools.file_tools import build_file_read_tool, build_file_write_tool, build_file_list_tool
from tools.web_search import build_web_search_tool
from tools.rag_builder import build_rag_builder_tool
from tools.image_analyzer import build_image_analyzer_tool
from tools.python_executor import build_python_executor_tool
from tools.python_plotter import build_python_plotter_tool
from agent.graph import AgentGraph
from api.routes import router, set_agent_instance
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def load_config():
    """Load configuration files"""
    config_dir = Path(__file__).parent / "config"

    # Load LLM configuration
    llm_config_path = config_dir / "llm_config.yaml"
    if llm_config_path.exists():
        with open(llm_config_path, "r", encoding="utf-8") as f:
            llm_config = yaml.safe_load(f)
    else:
        # Default configuration
        llm_config = {
            "default": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "api_key": os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
            },
            "planner": {
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "executor": {
                "temperature": 0.3,
                "max_tokens": 4000
            }
        }

    # Load Agent configuration
    agent_config_path = config_dir / "agent_config.yaml"
    if agent_config_path.exists():
        with open(agent_config_path, "r", encoding="utf-8") as f:
            agent_config = yaml.safe_load(f)
    else:
        agent_config = {
            "session": {
                "checkpoint_path": "checkpoints.sqlite",
                "single_user": True
            },
            "planner": {
                "hitl_enabled": True,
                "max_retries": 3
            },
            "executor": {
                "max_retries": 3,
                "verbose": False
            }
        }

    return llm_config, agent_config


def create_llm(config: dict, model_type: str = "default") -> ChatOpenAI:
    """
    Create LLM instance

    Args:
        config: LLM configuration dictionary
        model_type: Model type ("default", "planner", "executor")

    Returns:
        ChatOpenAI instance
    """
    # Get configuration for the specified type
    type_config = config.get(model_type, {})
    default_config = config.get("default", {})

    # Merge configurations (type_config takes priority)
    final_config = {**default_config, **type_config}

    return ChatOpenAI(
        model=final_config.get("model", "deepseek-chat"),
        base_url=final_config.get("base_url", "https://api.deepseek.com"),
        api_key=final_config.get("api_key", os.getenv("DEEPSEEK_API_KEY", "")),
        temperature=final_config.get("temperature", 0.7),
        max_tokens=final_config.get("max_tokens", 2000)
    )


def init_tool_registry() -> ToolRegistry:
    """
    Initialize tool registry

    Returns:
        ToolRegistry instance
    """
    registry = ToolRegistry()

    # Register file operation tools
    registry.register(
        tool=build_file_read_tool(),
        category="file",
        tags=["file", "read"],
        description_override="Read file content"
    )

    registry.register(
        tool=build_file_write_tool(),
        category="file",
        tags=["file", "write"],
        description_override="Write file content"
    )

    registry.register(
        tool=build_file_list_tool(),
        category="file",
        tags=["file", "list"],
        description_override="List directory contents"
    )

    # Web search tool
    registry.register(
        tool=build_web_search_tool(),
        category="search",
        tags=["web", "search", "internet", "tavily"],
        description_override="Web search tool. Uses Tavily search engine to search for latest information, news, data, etc. on the internet."
    )

    # # RAG builder tool
    # registry.register(
    #     tool=build_rag_builder_tool(),
    #     category="rag",
    #     tags=["rag", "knowledge-base", "retrieval"],
    #     description_override="Retrieval Augmented Generation (RAG) builder tool. Used for building knowledge bases from document libraries, supporting document indexing and semantic retrieval."
    # )

    # # Image analyzer tool
    # registry.register(
    #     tool=build_image_analyzer_tool(),
    #     category="vision",
    #     tags=["image", "vision", "ocr"],
    #     description_override="Image analysis tool. Uses vision language models (VLM) to parse image content, extracting text, objects, scenes, and other information from images."
    # )

    # # Python code executor tool
    # registry.register(
    #     tool=build_python_executor_tool(),
    #     category="code",
    #     tags=["python", "execution", "computation"],
    #     description_override="Python code execution tool (non-plotting). Used for executing Python code for data processing, computation, text analysis, and other logical operations."
    # )

    # # Python plotting tool
    # registry.register(
    #     tool=build_python_plotter_tool(),
    #     category="visualization",
    #     tags=["python", "plotting", "matplotlib", "visualization"],
    #     description_override="Python plotting tool. Specialized for creating various charts using matplotlib library, including bar charts, line charts, pie charts, scatter plots, and other data visualizations."
    # )

    return registry


def create_app() -> FastAPI:
    """
    Create FastAPI application

    Returns:
        FastAPI application instance
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Lumina Agent starting...")
    logger.info("=" * 50)

    # Load configuration
    llm_config, agent_config = load_config()

    # Initialize tool registry
    tool_registry = init_tool_registry()
    logger.info(f"Registered {len(tool_registry.list_tools())} tools")

    # Initialize LLM
    planner_llm = create_llm(llm_config, "planner")
    executor_llm = create_llm(llm_config, "executor")

    # Get checkpoint path
    checkpoint_path = agent_config.get("session", {}).get(
        "checkpoint_path", "checkpoints.sqlite"
    )

    # Initialize Agent
    agent = AgentGraph(
        planner_llm=planner_llm,
        executor_llm=executor_llm,
        tool_registry=tool_registry,
        checkpoint_path=checkpoint_path
    )
    logger.info("Agent graph initialized")

    # Set agent instance
    set_agent_instance(agent)

    # Create FastAPI application
    app = FastAPI(
        title="Lumina Agent",
        description="Dual-agent collaboration system based on LangGraph",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(router, prefix="/api")
    logger.info("API routes registered")

    @app.get("/")
    async def root():
        return {
            "message": "Lumina Agent API",
            "status": "running",
            "docs": "/docs"
        }

    logger.info("=" * 50)
    logger.info("Lumina Agent started successfully!")
    logger.info(f"API documentation: http://localhost:8000/docs")
    logger.info("=" * 50)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
