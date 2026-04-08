"""
Agent State Definition Module

Define state models used by LangGraph state diagrams
"""

from typing import TypedDict, List, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class PlannerContext(TypedDict, total=False):
    """
    Planner context (deprecated, kept for backward compatibility)
    """
    system_messages: List[dict]  # System messages
    user_messages: List[dict]    # User messages
    ai_messages: List[dict]      # AI responses
    tool_descriptions: List[dict]  # Tool descriptions


class AgentState(TypedDict, total=False):
    """
    Agent global state

    Passed and updated in LangGraph state diagram
    """
    # New: Session ID (for database operations)
    session_id: str

    # New: Current round (for managing message context)
    current_round: int

    # Message history (using add_messages to ensure append instead of overwrite)
    planner_messages: Annotated[List[BaseMessage], add_messages]

    # Planning results
    todo_list: List[dict]        # Task list, each task contains {id, description, tool}
    tool_list: List[dict]        # Tool list, subset of tools selected by Planner

    # Execution results
    execution_results: dict

    # Configuration
    thread_id: str

    # Executor internal state (for ReAct loop)
    executor_messages: Annotated[List[BaseMessage], add_messages]  # Executor conversation history
    current_todo_index: int      # Current executing task index
