"""
LangGraph State Graph Construction Module

Build and manage Agent state flows

New Architecture (after Executor split):
START → planner ─[interrupt]─→ executor_agent ↔ executor_tools → executor_final → END
         ↑                    │
         └──[Command(resume)]─┘
"""

from typing import List, Dict, Any, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Overwrite
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.language_models import BaseChatModel
import uuid
import json
import asyncio

from .state import AgentState
from .planner import AgentPlanner
from .executor import AgentExecutor


class AgentGraph:
    """
    Agent state graph constructor

    State Flow:
    START → planner ─[interrupt]─→ executor → END
             ↑                    │
             └──[Command(resume)]─┘

    Use SQLite checkpoint for session state storage
    """

    def __init__(
        self,
        planner_llm: BaseChatModel,
        executor_llm: BaseChatModel,
        tool_registry=None,
        checkpoint_path: str = "checkpoints.sqlite"
    ):
        """
        Initialize Agent state graph

        Args:
            planner_llm: Language model for Planner
            executor_llm: Language model for Executor
            tool_registry: Tool registry instance
            checkpoint_path: SQLite checkpoint file path, ":memory:" for in-memory database (testing)
        """
        self.planner = AgentPlanner(planner_llm, tool_registry)
        self.executor = AgentExecutor(executor_llm)
        self.tool_registry = tool_registry

        # Initialize checkpoint - create instance directly instead of using context manager
        import sqlite3
        if checkpoint_path == ":memory:":
            # Test environment: use in-memory database
            conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            # Production environment: use file database
            conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(conn)

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build state graph"""
        builder = StateGraph(AgentState)

        # Add Planner node
        builder.add_node("planner", self.planner_node)

        # Executor split into three nodes
        builder.add_node("executor_agent", self.executor_agent_node)
        builder.add_node("executor_tools", self.executor_tools_node)
        builder.add_node("executor_final", self.executor_final_node)

        # Set entry point
        builder.set_entry_point("planner")

        # Planner → Executor Agent / Planner (conditional edge routing)
        # If todo_list is not empty, route to executor_agent; otherwise route back to planner (user rejection case)
        builder.add_conditional_edges(
            "planner",
            self._route_planner_output,
            {
                "execute": "executor_agent",  # Has tasks to execute
                "replan": "planner"           # User rejected, re-plan
            }
        )

        # Executor internal ReAct loop: route based on presence of tool_calls
        builder.add_conditional_edges(
            "executor_agent",
            self.executor.should_continue,
            {
                "tools": "executor_tools",  # Has tool calls, execute tools
                "final": "executor_final"   # No tool calls, enter final
            }
        )

        # Return to executor_agent after tool execution
        builder.add_edge("executor_tools", "executor_agent")

        # Executor Final → END / executor_agent (conditional edge routing)
        # If all tasks completed, route to END; otherwise route back to executor_agent to continue next task
        builder.add_conditional_edges(
            "executor_final",
            self._route_executor_final,
            {
                "end": END,                    # All tasks completed
                "continue": "executor_agent"   # More tasks to execute
            }
        )

        # Compile and enable checkpoint
        return builder.compile(checkpointer=self.checkpointer)

    def _route_planner_output(self, state: AgentState) -> Literal["execute", "replan"]:
        """
        Route based on planner output

        Args:
            state: Current state

        Returns:
            "execute" if there is todo_list, otherwise "replan"
        """
        todo_list = state.get("todo_list", [])
        if todo_list:
            return "execute"
        else:
            return "replan"

    def _route_executor_final(self, state: AgentState) -> Literal["end", "continue"]:
        """
        Route based on executor_final output

        Args:
            state: Current state

        Returns:
            "end" if all tasks completed, otherwise "continue"
        """
        todo_list = state.get("todo_list", [])
        current_index = state.get("current_todo_index", 0)
        if current_index >= len(todo_list):
            return "end"
        else:
            return "continue"

    def planner_node(self, state: AgentState) -> AgentState:
        """
        Planner node

        Args:
            state: Current state

        Returns:
            Updated state
        """
        result = self.planner.plan(state)

        # If user confirmed (has todo_list), increment current_round
        # This way next round of conversation will use new round
        if result.get("todo_list"):
            current_round = state.get("current_round", 1)
            result["current_round"] = current_round + 1
            # Clear executor_messages, ensure new round of conversation starts from clean state
            # Use Overwrite instead of empty list, ensure bypass reducer
            result["executor_messages"] = Overwrite([])
            # Also reset task index
            result["current_todo_index"] = 0
            # Clear execution_results, avoid accumulating previous round's results
            result["execution_results"] = Overwrite({})

        return result

    # def executor_node(self, state: AgentState) -> AgentState:
    #     """
    #     Executor node (deprecated, kept for backward compatibility)

    #     Args:
    #         state: Current state

    #     Returns:
    #         Updated state
    #     """
    #     return self.executor.execute(state) if hasattr(self.executor, 'execute') else {}

    def executor_agent_node(self, state: AgentState) -> AgentState:
        """
        Executor Agent Node: Call LLM, decide next action

        Args:
            state: Current state

        Returns:
            Updated state
        """
        # Ensure Executor has tools
        tool_list = state.get("tool_list", [])
        if tool_list and self.executor.tool_node is None:
            # Extract tool instances from tool_list
            tools = []
            for item in tool_list:
                if isinstance(item, dict) and "tool" in item:
                    tools.append(item["tool"])

            # If tool_list contains tool names, get instances from registry
            if not tools and self.tool_registry:
                for item in tool_list:
                    if isinstance(item, dict):
                        tool_name = item.get("name")
                        tool = self.tool_registry.get_tool(tool_name)
                        if tool:
                            tools.append(tool)

            if tools:
                self.executor.set_tools(tools)

        # Ensure Executor has database instance
        # Get session_id from state and create database instance
        session_id = state.get("session_id")
        if session_id:
            from database.connection import SessionDatabase
            if not hasattr(self, 'db') or self.db is None:
                self.db = SessionDatabase(session_id)
            self.executor.set_database(self.db)

        return self.executor.executor_agent_node(state)

    def executor_tools_node(self, state: AgentState) -> AgentState:
        """
        Executor Tools Node: Use ToolNode to execute tools

        Args:
            state: Current state

        Returns:
            Updated state
        """
        return self.executor.executor_tools_node(state)

    def executor_final_node(self, state: AgentState) -> AgentState:
        """
        Executor Final Node: Integrate results, return final answer

        Args:
            state: Current state

        Returns:
            Updated state
        """
        return self.executor.executor_final_node(state)

    def invoke(
        self,
        user_input: str,
        thread_id: str,
        session_id: str = None,
        files: List[str] = None
    ) -> dict:
        """
        Invoke Agent

        Args:
            user_input: User input
            thread_id: Thread ID (for LangGraph checkpoint)
            session_id: Session ID (for database)
            files: File path list (backward compatible, deprecated)

        Returns:
            Agent response
        """
        config = {"configurable": {"thread_id": thread_id}}

        # If session_id is not provided, generate a new one
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())

        # Initialize database
        from database.connection import SessionDatabase
        self.db = SessionDatabase(session_id)

        # Process files (if any)
        if files:
            from services.session_service import SessionService
            SessionService.process_files(
                session_id=session_id,
                file_paths=files
            )

        # Set database instances for Planner and Executor
        self.planner.set_database(self.db)
        self.executor.set_database(self.db)

        # Get existing state from checkpoint (multi-round conversation)
        existing_state = self.get_state(thread_id)

        # Determine current round: restore from existing state, or load from database
        current_round = 1
        planner_messages = []
        execution_results = {}

        if existing_state:
            # Restore from checkpoint
            planner_messages = list(existing_state.get("planner_messages", []))
            # Restore execution results (if any)
            execution_results = existing_state.get("execution_results", {})
            # Restore current_round from messages (take max round + 1)
            for msg in planner_messages:
                msg_round = (msg.metadata or {}).get("round", 0)
                if msg_round > 0:
                    current_round = max(current_round, msg_round + 1)
        elif session_id:
            # Load historical messages from database
            from database.connection import SessionDatabase
            db = SessionDatabase(session_id)
            messages = db.get_messages(thread_id=thread_id, limit=50)
            if messages:
                for msg in messages:
                    langchain_msg = self.planner._convert_to_langchain_message(msg)
                    planner_messages.append(langchain_msg)
                # Restore current_round from messages
                for msg in planner_messages:
                    msg_round = (msg.metadata or {}).get("round", 0)
                    if msg_round > 0:
                        current_round = max(current_round, msg_round + 1)

        # Build initial state
        initial_state = {
            "session_id": session_id,
            "current_round": current_round,  # Use restored round
            "planner_messages": planner_messages,
            "todo_list": [],
            "tool_list": [],
            "execution_results": execution_results,  # Use restored execution results
            "thread_id": thread_id,
            "executor_messages": [],
            "current_todo_index": 0
        }

        # Add user message (using current round)
        initial_state["planner_messages"].append(
            HumanMessage(content=user_input, metadata={"round": current_round})
        )

        # Invoke graph
        result = self.graph.invoke(initial_state, config)

        # Asynchronously sync messages to database (non-blocking)
        self._schedule_sync_messages_to_database(thread_id, session_id)

        return result

    def get_state(self, thread_id: str) -> dict:
        """
        Get current state

        Args:
            thread_id: Session ID

        Returns:
            Current state values
        """
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)
        return dict(state.values) if state else {}

    def get_interrupt_info(self, thread_id: str) -> Optional[dict]:
        """
        Get interrupt information

        Args:
            thread_id: Session ID

        Returns:
            Interrupt information (if any), including todo_list, tool_list, etc.
        """
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)

        if not state:
            return None

        # Check if there are pending tasks (indicating interrupt waiting for confirmation)
        todo_list = state.values.get("todo_list", [])
        tool_list = state.values.get("tool_list", [])

        if todo_list:
            return {
                "todo_list": todo_list,
                "tool_list": tool_list
            }

        return None

    def get_execution_result(self, thread_id: str) -> dict:
        """
        Get execution result

        Args:
            thread_id: Session ID

        Returns:
            Execution result
        """
        state = self.get_state(thread_id)
        return state.get("execution_results", {})

    def _schedule_sync_messages_to_database(self, thread_id: str, session_id: str):
        """
        Asynchronously schedule message sync task

        Use asyncio.create_task for non-blocking sync
        If no running event loop (test environment), execute synchronously
        """
        try:
            loop = asyncio.get_running_loop()
            # Has running event loop, create async task
            asyncio.create_task(self._sync_messages_to_database(thread_id, session_id))
        except RuntimeError:
            # No running event loop (test environment), execute synchronously
            asyncio.run(self._sync_messages_to_database(thread_id, session_id))

    async def _sync_messages_to_database(self, thread_id: str, session_id: str):
        """
        Sync messages from checkpoint to database

        Only save new messages (avoid duplicates)
        """
        if not hasattr(self, 'db') or self.db is None:
            return

        try:
            # Get current state
            state = self.get_state(thread_id)
            planner_messages = state.get("planner_messages", [])

            if not planner_messages:
                return

            # Get saved messages from database
            saved_messages = self.db.get_messages(thread_id=thread_id, limit=100)
            saved_ids = {msg.get('id') for msg in saved_messages}

            # Only save new messages
            for msg in planner_messages:
                msg_id = self._get_message_id(msg)
                if msg_id and msg_id not in saved_ids:
                    # Convert to database format
                    db_msg = self._convert_to_db_message(msg, session_id, thread_id)
                    self.db.add_message(**db_msg)

            # Sync execution_results to database
            execution_results = state.get("execution_results", {})
            if execution_results and execution_results.get("status") == "completed":
                current_round = state.get("current_round", 1)
                # Generate unique message ID (includes round to distinguish different rounds)
                result_msg_id = f"exec_result_{thread_id}_round_{current_round}"

                # Check if already exists
                if result_msg_id not in saved_ids:
                    # Format as readable text
                    result_text = self._format_execution_results(execution_results)

                    # Add to database (as AI message)
                    self.db.add_message(
                        message_id=result_msg_id,
                        thread_id=thread_id,
                        role="ai",
                        content=result_text,
                        metadata={"type": "execution_result", "round": current_round}
                    )
        except Exception as e:
            # Record error but don't affect main flow
            print(f"Failed to sync messages to database: {e}")

    def _get_message_id(self, msg) -> Optional[str]:
        """Get message ID"""
        if hasattr(msg, 'id') and msg.id:
            return msg.id
        if isinstance(msg, dict) and 'id' in msg:
            return msg.get('id')
        return None

    def _convert_to_db_message(self, msg, session_id: str, thread_id: str) -> dict:
        """Convert LangChain message to database format"""
        if isinstance(msg, HumanMessage):
            role = "human"
        elif isinstance(msg, AIMessage):
            role = "ai"
        elif isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, ToolMessage):
            role = "tool"
        else:
            role = "unknown"

        # Get message ID
        msg_id = self._get_message_id(msg)
        if not msg_id:
            msg_id = str(uuid.uuid4())

        # Process tool_calls
        tool_calls = None
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            tool_calls = json.dumps(msg.tool_calls, ensure_ascii=False)

        # Get content
        content = ""
        if hasattr(msg, 'content') and msg.content:
            content = msg.content

        # Get tool_call_id
        tool_call_id = None
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id'):
            tool_call_id = msg.tool_call_id

        # Get metadata (SystemMessage may not have metadata attribute)
        metadata = None
        if hasattr(msg, 'metadata') and msg.metadata:
            metadata = msg.metadata

        return {
            "message_id": msg_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "metadata": metadata
        }

    def _format_execution_results(self, results: dict) -> str:
        """Format execution_results as readable text"""
        if not results:
            return "No execution results"

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
