"""
FastAPI Routes Module

Define API endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional, List, Dict, Any
import uuid
import uuid
import tempfile
import os

from langgraph.types import Command
from langgraph.errors import GraphInterrupt

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .schemas import (
    ChatRequest,
    ChatResponse,
    ConfirmRequest,
    ConfirmResponse,
    RejectRequest,
    RejectResponse,
    StatusResponse,
    ConfigGetResponse,
    ConfigUpdateRequest,
    ConfigUpdateResponse,
)

router = APIRouter()

# Global Agent instance (initialized at startup)
_agent_instance = None


def set_agent_instance(agent_instance):
    """
    Set Agent instance

    Args:
        agent_instance: AgentGraph instance
    """
    global _agent_instance
    _agent_instance = agent_instance


def get_agent_instance():
    """Get Agent instance"""
    if _agent_instance is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return _agent_instance


def format_execution_results(results: dict) -> str:
    """Format execution_results as readable text"""
    if not results:
        return "No execution results"

    if results.get("status") == "completed":
        result_list = results.get("results", [])
        if not result_list:
            return "No detailed results"

        summaries = []
        for item in result_list:
            task_id = item.get("task_id", "unknown")
            status = item.get("status", "unknown")
            result = item.get("result", "")
            summaries.append(f"- Task {task_id} [{status}]: {result}")
        return "\n".join(summaries)

    return str(results)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Start a conversation

    Receive user message and optional file list, return planning result waiting for confirmation
    Supports multi-turn conversation: if thread_id is provided, reuse the session and inject previous round's execution results

    Args:
        request: Chat request

    Returns:
        Response containing thread_id and planning result
    """
    agent = get_agent_instance()

    # Reuse thread_id for multi-turn conversation; otherwise generate a new one
    thread_id = request.thread_id if request.thread_id else str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Check if it's a new round of conversation (has historical state)
    existing_state = agent.get_state(thread_id)
    is_multi_turn = existing_state and existing_state.get("planner_messages")

    # If session_id is not provided, create a new session
    if not request.session_id:
        from services.session_service import SessionService
        session_info = SessionService.create_session(title="New Session")
        request.session_id = session_info["id"]

    # [Optimization] If no messages in checkpoint but has session_id, load history from database
    if request.session_id and (not is_multi_turn or not existing_state.get("planner_messages")):
        # Load messages from database to restore to checkpoint
        from database.connection import SessionDatabase
        db = SessionDatabase(request.session_id)
        messages = db.get_messages(thread_id=thread_id, limit=50)

        if messages:
            # Convert message format
            langchain_messages = []
            for msg in messages:
                langchain_messages.append(agent.planner._convert_to_langchain_message(msg))

            # Update state
            agent.graph.update_state(config, {
                "planner_messages": langchain_messages,
                "session_id": request.session_id
            })

    # Process files (if files parameter is provided)
    # Use SessionService.process_files to process files and store to database
    if request.files:
        from services.session_service import SessionService
        SessionService.process_files(
            session_id=request.session_id,
            file_paths=request.files
        )

    try:
        # Build initial state (reuse agent.invoke() internal logic)
        existing_state = agent.get_state(thread_id)

        current_round = 1
        planner_messages = []
        execution_results = {}

        if existing_state:
            planner_messages = list(existing_state.get("planner_messages", []))
            execution_results = existing_state.get("execution_results", {})
            for msg in planner_messages:
                msg_round = (msg.metadata or {}).get("round", 0)
                if msg_round > 0:
                    current_round = max(current_round, msg_round + 1)

        # Build initial state
        initial_state = {
            "session_id": request.session_id,
            "current_round": current_round,
            "planner_messages": planner_messages + [HumanMessage(content=request.message, metadata={"round": current_round})],
            "todo_list": [],
            "tool_list": [],
            "execution_results": execution_results,
            "thread_id": thread_id,
            "executor_messages": [],
            "current_todo_index": 0
        }

        # Set database instance
        if request.session_id:
            from database.connection import SessionDatabase
            agent.db = SessionDatabase(request.session_id)
            agent.planner.set_database(agent.db)
            agent.executor.set_database(agent.db)

        # Directly use stream() to avoid double calling LLM
        interrupt_chunk = None
        for chunk in agent.graph.stream(initial_state, config):
            if "__interrupt__" in chunk:
                interrupt_chunk = chunk
                break

        if interrupt_chunk:
            # Interrupt occurred, return interrupt information
            interrupt_info = interrupt_chunk["__interrupt__"][0]

            # Asynchronously sync messages to database
            if request.session_id:
                agent._schedule_sync_messages_to_database(thread_id, request.session_id)

            return ChatResponse(
                thread_id=thread_id,
                status="interrupted",
                todo_list=interrupt_info.value.get("todo_list", []),
                tool_list=interrupt_info.value.get("tool_list", []),
                interrupt_info=interrupt_info.value
            )

        # Completed normally
        state = agent.get_state(thread_id)

        # Asynchronously sync messages to database
        if request.session_id:
            agent._schedule_sync_messages_to_database(thread_id, request.session_id)

        # Convert planner_messages to frontend-available format
        messages = []
        planner_messages = state.get("planner_messages", [])
        for msg in planner_messages:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                role = "human" if isinstance(msg, HumanMessage) else ("ai" if isinstance(msg, AIMessage) else "system")
                # Skip system messages, not needed for frontend display
                if role == "system":
                    continue
                msg_data = {
                    "id": msg.id or str(uuid.uuid4()),
                    "type": role,
                    "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                    "metadata": getattr(msg, 'metadata', {}) or {}
                }
                messages.append(msg_data)

        return ChatResponse(
            thread_id=thread_id,
            status="completed",
            result=state.get("execution_results", {}),
            messages=messages
        )

    except GraphInterrupt:
        # Interrupted, get interrupt information
        interrupt_info = agent.get_interrupt_info(thread_id)
        if interrupt_info:
            return ChatResponse(
                thread_id=thread_id,
                status="interrupted",
                todo_list=interrupt_info.get("todo_list", []),
                tool_list=interrupt_info.get("tool_list", []),
                interrupt_info=interrupt_info
            )
        raise HTTPException(500, "Interrupt handling failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm(request: ConfirmRequest):
    """
    User confirms plan

    Confirm the plan generated by Planner, start execution

    Args:
        request: Confirm request

    Returns:
        Execution result
    """
    agent = get_agent_instance()
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        # Get session_id (for message sync)
        state_before = agent.get_state(request.thread_id)
        session_id = state_before.get("session_id")

        # Use Command to resume execution
        for chunk in agent.graph.stream(
            Command(resume={"action": "approve"}),
            config
        ):
            pass

        # Get latest state
        state = agent.get_state(request.thread_id)

        # Convert planner_messages to frontend-available format
        messages = []
        planner_messages = state.get("planner_messages", [])
        for msg in planner_messages:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                role = "human" if isinstance(msg, HumanMessage) else ("ai" if isinstance(msg, AIMessage) else "system")
                # Skip system messages, not needed for frontend display
                if role == "system":
                    continue
                msg_data = {
                    "id": msg.id or str(uuid.uuid4()),
                    "type": role,
                    "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                    "metadata": getattr(msg, 'metadata', {}) or {}
                }
                messages.append(msg_data)

        # Sync messages to database (AI messages generated by executor)
        # Use await to wait for sync completion, avoid race conditions
        if session_id:
            await agent._sync_messages_to_database(request.thread_id, session_id)

        return ConfirmResponse(
            thread_id=request.thread_id,
            status="completed",
            result=state.get("execution_results", {}),
            messages=messages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject", response_model=RejectResponse)
async def reject(request: RejectRequest):
    """
    User rejects plan

    Reject the plan generated by Planner, and provide feedback for re-planning

    Args:
        request: Reject request

    Returns:
        Re-planning result
    """
    agent = get_agent_instance()
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        # Get session_id (for message sync)
        state_before = agent.get_state(request.thread_id)
        session_id = state_before.get("session_id")

        # Use Command to resume execution, pass in rejection reason
        for chunk in agent.graph.stream(
            Command(resume={"action": "reject", "reason": request.feedback}),
            config
        ):
            # If re-planning, may trigger interrupt again
            if "__interrupt__" in chunk:
                interrupt_info = chunk["__interrupt__"][0]

                # Get latest state (for returning messages)
                state_after = agent.get_state(request.thread_id)

                # Convert planner_messages to frontend-available format
                messages = []
                planner_messages = state_after.get("planner_messages", [])
                for msg in planner_messages:
                    if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                        role = "human" if isinstance(msg, HumanMessage) else ("ai" if isinstance(msg, AIMessage) else "system")
                        # Skip system messages, not needed for frontend display
                        if role == "system":
                            continue
                        msg_data = {
                            "id": msg.id or str(uuid.uuid4()),
                            "type": role,
                            "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                            "metadata": getattr(msg, 'metadata', {}) or {}
                        }
                        messages.append(msg_data)

                return RejectResponse(
                    thread_id=request.thread_id,
                    status="pending_confirmation",
                    result={
                        "todo_list": interrupt_info.value.get("todo_list", []),
                        "tool_list": interrupt_info.value.get("tool_list", [])
                    },
                    messages=messages
                )

        # Get latest state
        state = agent.get_state(request.thread_id)

        # Convert planner_messages to frontend-available format
        messages = []
        planner_messages = state.get("planner_messages", [])
        for msg in planner_messages:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                role = "human" if isinstance(msg, HumanMessage) else ("ai" if isinstance(msg, AIMessage) else "system")
                # Skip system messages, not needed for frontend display
                if role == "system":
                    continue
                msg_data = {
                    "id": msg.id or str(uuid.uuid4()),
                    "type": role,
                    "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                    "metadata": getattr(msg, 'metadata', {}) or {}
                }
                messages.append(msg_data)

        # Sync messages to database
        # Use await to wait for sync completion, avoid race conditions
        if session_id:
            await agent._sync_messages_to_database(request.thread_id, session_id)

        return RejectResponse(
            thread_id=request.thread_id,
            status="completed",
            result=state.get("execution_results", {}),
            messages=messages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{thread_id}", response_model=StatusResponse)
async def get_status(thread_id: str):
    """
    Get session status

    Args:
        thread_id: Session ID

    Returns:
        Current session status
    """
    agent = get_agent_instance()

    try:
        state = agent.get_state(thread_id)
        interrupt_info = agent.get_interrupt_info(thread_id)

        return StatusResponse(
            thread_id=thread_id,
            todo_list=state.get("todo_list", []),
            tool_list=state.get("tool_list", []),
            execution_results=state.get("execution_results", {}),
            has_pending_interrupt=interrupt_info is not None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "agent_initialized": _agent_instance is not None
    }


@router.post("/session/{session_id}/load")
async def load_session(session_id: str, thread_id: Optional[str] = None):
    """
    Load session history messages to state

    Used for restoring context when user switches sessions

    Args:
        session_id: Session ID to load
        thread_id: Optional thread ID, if not provided get original thread_id from database

    Returns:
        Loaded message count and thread_id
    """
    agent = get_agent_instance()

    # Load messages from database (do not pass thread_id, get all messages for this session)
    from database.connection import SessionDatabase
    db = SessionDatabase(session_id)
    all_messages = db.get_messages(thread_id=None, limit=50)

    # Get original thread_id from messages (take thread_id from first message)
    if not thread_id:
        if all_messages and all_messages[0].get('thread_id'):
            thread_id = all_messages[0]['thread_id']
        else:
            # If no messages, generate a new thread_id
            thread_id = str(uuid.uuid4())

    # Filter messages by thread_id (ensure only messages from this thread are loaded)
    messages = [msg for msg in all_messages if msg.get('thread_id') == thread_id]

    # Restore messages to checkpoint
    # Use LangGraph's update_state API
    config = {"configurable": {"thread_id": thread_id}}

    # Convert message format, and add round metadata to each message
    langchain_messages = []
    for idx, msg in enumerate(messages):
        langchain_msg = agent.planner._convert_to_langchain_message(msg)
        # Add round metadata to message (starting from 1)
        # SystemMessage is round=0, other messages are assigned round in order
        if isinstance(langchain_msg, SystemMessage):
            langchain_msg.metadata = {"round": 0}
        else:
            # Calculate round based on message index (every 3 messages per round: Human + AI + Tool/Result)
            round_num = (idx // 3) + 1
            langchain_msg.metadata = {"round": round_num}
        langchain_messages.append(langchain_msg)

    # Calculate current round (based on message count)
    current_round = (len(messages) // 3) + 1 if messages else 1

    # Update state
    agent.graph.update_state(config, {
        "planner_messages": langchain_messages,
        "session_id": session_id,
        "current_round": current_round
    })

    return {
        "thread_id": thread_id,
        "session_id": session_id,
        "loaded_message_count": len(messages),
        "current_round": current_round
    }


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str, thread_id: Optional[str] = None, limit: int = 50):
    """
    Get session history messages

    Args:
        session_id: Session ID
        thread_id: Optional thread ID, used to filter messages for specific thread
        limit: Maximum number of messages to return

    Returns:
        Message list
    """
    from database.connection import SessionDatabase
    db = SessionDatabase(session_id)
    messages = db.get_messages(thread_id=thread_id, limit=limit)

    return {
        "session_id": session_id,
        "messages": messages
    }


# ========== File Upload Related Endpoints ==========

def get_temp_dir() -> str:
    """Get temporary directory for storing uploaded files"""
    temp_dir = os.path.join(tempfile.gettempdir(), "lumina_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


@router.post("/upload")
async def upload_files(
    session_id: Optional[str] = None,
    files: List[UploadFile] = File(...)
):
    """
    Upload and process files

    Args:
        session_id: Optional session ID, create a new one if not provided
        files: List of uploaded files

    Returns:
        Session ID and processed file information
    """
    try:
        # If session_id is not provided, create a new session
        if session_id is None:
            from services.session_service import SessionService
            session_info = SessionService.create_session()
            session_id = session_info["id"]

        # Save uploaded files to temporary directory
        temp_dir = get_temp_dir()
        file_paths = []

        for file in files:
            # Generate a unique filename
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(temp_dir, unique_filename)

            # Save file
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            file_paths.append(file_path)

        # Process files and store to database
        from services.session_service import SessionService
        processed_items = SessionService.process_files(
            session_id=session_id,
            file_paths=file_paths
        )

        # Clean up temporary files
        for file_path in file_paths:
            try:
                os.remove(file_path)
            except Exception:
                pass

        return {
            "session_id": session_id,
            "processed_items": [
                {
                    "id": item["id"],
                    "type": item["processed_type"],
                    "filename": item["original_filename"]
                }
                for item in processed_items
            ]
        }

    except Exception as e:
        # Clean up temporary files (if error occurs)
        for file_path in file_paths:
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/files")
async def get_session_files(session_id: str):
    """
    Get file metadata list for the session

    Args:
        session_id: Session ID

    Returns:
        List of file metadata
    """
    try:
        from database.connection import SessionDatabase
        db = SessionDatabase(session_id)
        metadata_list = db.get_file_metadata_by_session()

        return {
            "session_id": session_id,
            "metadata": metadata_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    """
    Get list of all sessions

    Returns:
        List of session info
    """
    try:
        from services.session_service import SessionService
        sessions = SessionService.list_sessions()

        return {
            "sessions": [
                {
                    "id": s["id"],
                    "title": s.get("title"),
                    "created_at": s.get("created_at"),
                    "updated_at": s.get("updated_at"),
                    "status": s.get("status")
                }
                for s in sessions
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete session and all its data

    Args:
        session_id: Session ID

    Returns:
        Delete result
    """
    try:
        from services.session_service import SessionService
        result = SessionService.delete_session(session_id)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def create_session(title: Optional[str] = None):
    """
    Create a new session

    Args:
        title: Optional session title

    Returns:
        Newly created session info
    """
    try:
        from services.session_service import SessionService
        session_info = SessionService.create_session(title=title)
        return session_info

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Configuration Management Endpoints ==========

@router.get("/config", response_model=ConfigGetResponse)
async def get_config():
    """
    Get current configuration

    Returns LLM configuration and Agent configuration

    Returns:
        Current configuration
    """
    try:
        from config.config_manager import get_config_manager
        config_manager = get_config_manager()
        all_config = config_manager.get_all_config()

        # Note: Does not return sensitive API Key
        safe_llm_config = {}
        for section, config in all_config["llm"].items():
            safe_llm_config[section] = {k: v for k, v in config.items() if k != "api_key"}

        return ConfigGetResponse(
            llm=safe_llm_config,
            agent=all_config["agent"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=ConfigUpdateResponse)
async def update_config(request: ConfigUpdateRequest):
    """
    Update configuration

    Update LLM configuration and/or Agent configuration

    Args:
        request: Configuration update request

    Returns:
        Updated configuration
    """
    try:
        from config.config_manager import get_config_manager
        config_manager = get_config_manager()

        updated_llm = None
        updated_agent = None

        # Update LLM configuration
        if request.llm:
            for section, values in request.llm.items():
                # Special handling: if api_key is provided and value is "***HIDDEN***", keep original value
                if section in ["default", "planner", "executor"]:
                    current_config = config_manager.get_llm_config(section)
                    if "api_key" in values and values["api_key"] == "***HIDDEN***":
                        values["api_key"] = current_config.get("api_key", "")
                    updated_llm = config_manager.update_llm_config(section, values)

        # Update Agent configuration
        if request.agent:
            for section, values in request.agent.items():
                if section in ["session", "planner", "executor", "tools"]:
                    updated_agent = config_manager.update_agent_config(section, values)

        # Clear cache for reload
        config_manager.clear_cache()

        return ConfigUpdateResponse(
            status="success",
            llm=updated_llm,
            agent=updated_agent
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
