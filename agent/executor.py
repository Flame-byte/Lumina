"""
Executor Agent Module

Responsible for executing specific tasks

Architecture Notes:
Executor is no longer a single node, but provides three node methods:
1. executor_agent_node: Call LLM, decide next action
2. executor_tools_node: Use ToolNode to automatically execute tools
3. executor_final_node: Integrate results, return final answer

State Flow:
executor_agent →(has tool_calls)→ executor_tools → executor_agent
            ↘(no tool_calls)→ executor_final → END
"""

from typing import List, Dict, Any, Literal
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from langgraph.types import Overwrite
import json
import uuid

from config.prompts.loader import get_prompt_loader


class AgentExecutor:
    """
    Agent Executor - Responsible for executing specific tasks

    Responsibilities:
    - Receive Planner's ToDo List and Tool List
    - Split into three nodes: executor_agent, executor_tools, executor_final
    - Use LangGraph ToolNode to automatically execute tool calls
    - Run in isolated context
    """

    def __init__(self, llm: BaseChatModel, max_retries: int = 3):
        """
        Initialize Executor

        Args:
            llm: Language model instance
            max_retries: Maximum retry count
        """
        self.llm = llm
        self.max_retries = max_retries
        self.prompt_loader = get_prompt_loader()
        self.tool_node = None  # Will be initialized later via set_tools()
        self.llm_with_tools = None  # LLM bound with tools
        self.db = None  # Database instance, will be set externally

    def set_database(self, db):
        """
        Set database instance

        Args:
            db: SessionDatabase instance
        """
        self.db = db

    def set_tools(self, tools: List[BaseTool]):
        """
        Set tool list and create ToolNode

        Args:
            tools: Tool instances list
        """
        self.tools = tools
        self.tool_node = ToolNode(tools)
        self.llm_with_tools = self.llm.bind_tools(tools)

    def executor_agent_node(self, state: dict) -> dict:
        """
        Executor Agent Node: Call LLM, decide next action

        Manage context using round field in message metadata:
        - round=1,2,3...: Each round of user request
        - All tasks in the same todo list share the same round number (provided by state["current_round"])

        Args:
            state: Current Agent state

        Returns:
            Dictionary containing executor_messages
        """
        todo_list = state.get("todo_list", [])
        current_index = state.get("current_todo_index", 0)

        # If all tasks completed, enter final
        if current_index >= len(todo_list):
            return self.executor_final_node(state)

        # Get current task
        current_todo = todo_list[current_index]
        task_description = current_todo.get("description", "")

        # Get current executor message history (maintained by reducer automatically)
        executor_messages = state.get("executor_messages", [])

        # Use state's current_round (set by planner), all tasks in the same todo list share the same round
        # This ensures that all tasks in the same plan share a unified context identifier
        task_round = state.get("current_round", 1)

        # Check if it's the first call (only system prompt or empty list)
        # Or check if it's a ReAct loop (last message is ToolMessage)
        is_first_call = len(executor_messages) == 0 or (
            len(executor_messages) == 1 and
            isinstance(executor_messages[0], SystemMessage)
        )

        # Check if it's a ReAct loop call (return to agent after tool execution)
        # If the last message is ToolMessage, it's a ReAct loop, no need to add new HumanMessage
        is_react_loop = (
            len(executor_messages) > 0 and
            isinstance(executor_messages[-1], ToolMessage)
        )

        if is_first_call:
            # First call: Initialize system prompt
            system_prompt = self.prompt_loader.get_execution_system_prompt(
                max_retries=self.max_retries
            )
            messages = [SystemMessage(content=system_prompt)]

            # Load file content from database
            if self.db:
                file_contents_content = self._format_file_contents_for_executor(
                    self.db.get_processed_data()
                )
                if file_contents_content:
                    # Add first task instruction (including file content)
                    task_instruction = f"Execute task: {task_description}"
                    content = self._build_content_with_files(task_instruction, file_contents_content)
                    messages.append(HumanMessage(content=content, metadata={"round": task_round}))
                else:
                    # No file content, add task instruction directly
                    messages.append(HumanMessage(
                        content=f"Execute task: {task_description}",
                        metadata={"round": task_round}
                    ))
            else:
                # No database, add task instruction directly
                messages.append(HumanMessage(
                    content=f"Execute task: {task_description}",
                    metadata={"round": task_round}
                ))

            # Call LLM
            if self.llm_with_tools is None:
                return {"executor_messages": []}

            response = self.llm_with_tools.invoke(messages)
            # Add round metadata to response
            response.metadata = {"round": task_round}

            # Return complete messages (SystemMessage + HumanMessage + AIMessage)
            # This way reducer can correctly accumulate complete context
            return {"executor_messages": messages + [response]}

        else:
            # Previous task completed, start new task
            # Accumulate complete context: use executor_messages + new task instruction
            # This way new task can access all previous tasks' execution results and conversation history
            # All tasks in the same todo list share the same task_round

            # Check if it's a ReAct loop (return to agent after tool execution)
            # If it's a ReAct loop, no need to add new HumanMessage, use existing context directly
            if is_react_loop:
                # ReAct loop: After tool execution, continue with same task
                # No need to add new HumanMessage, use existing messages to call LLM directly
                new_messages = executor_messages
            else:
                # New task starts: Add new HumanMessage
                new_human_message = HumanMessage(
                    content=f"Execute new task: {task_description}",
                    metadata={"round": task_round}
                )
                new_messages = executor_messages + [new_human_message]

            response = self.llm_with_tools.invoke(new_messages)
            # Add round metadata to response
            response.metadata = {"round": task_round}

            # Return new messages for reducer accumulation
            # ReAct loop: only return [AIMessage]
            # New task starts: return [HumanMessage, AIMessage]
            if is_react_loop:
                return {"executor_messages": [response]}
            else:
                return {"executor_messages": [new_human_message, response]}

    def _build_content_with_files(self, task_instruction: str, file_contents_content: List[Dict]) -> List[Dict]:
        """
        Build content array including file content

        Args:
            task_instruction: Task instruction text
            file_contents_content: File content list (each element is {"type": "text", "text": "..."} format)

        Returns:
            content array
        """
        content = [
            {"type": "text", "text": task_instruction}
        ]
        # Add file content
        content.extend(file_contents_content)
        return content

    def _format_file_contents_for_executor(self, processed_data_list: List[dict]) -> List[Dict]:
        """
        Format file content to Executor-compatible format (as part of HumanMessage content array)

        Args:
            processed_data_list: Processed data list

        Returns:
            Content list, each element is {"type": "text", "text": "..."} format
        """
        if not processed_data_list:
            return []

        contents = []
        for data in processed_data_list:
            file_type = data.get('file_type', 'unknown')
            filename = data.get('original_filename', 'unknown')
            content = data.get('content', '')
            processed_type = data.get('processed_type', 'unknown')

            if processed_type == 'text':
                contents.append(
                    {"type": "text", "text": f"[File: {filename}]\n{content}"}
                )
            elif processed_type == 'image':
                # Image content includes storage path
                storage_path = data.get('storage_path', '')
                contents.append(
                    {"type": "text", "text": f"[File: {filename}] (Image) Storage path: {storage_path}"}
                )
            elif processed_type == 'mixed':
                # Mixed content handling
                if isinstance(content, dict):
                    text_content = content.get('text', '')
                    images = content.get('images', [])
                    if text_content and images:
                        contents.append(
                            {"type": "text", "text": f"[File: {filename}] (Mixed)\n{text_content}\nImage paths: {', '.join(images)}"}
                        )
                    else:
                        contents.append(
                            {"type": "text", "text": f"[File: {filename}] (Mixed)\n{str(content)}"}
                        )
                else:
                    contents.append(
                        {"type": "text", "text": f"[File: {filename}] (Mixed)\n{content if isinstance(content, str) else str(content)}"}
                    )
            elif processed_type == 'structured_data':
                # Try to parse JSON
                json_content = content
                if isinstance(content, str):
                    try:
                        json_content = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        pass
                contents.append(
                    {"type": "text", "text": f"[File: {filename}] (Structured data)\n{json.dumps(json_content, ensure_ascii=False) if isinstance(json_content, (dict, list)) else content}"}
                )
            else:
                # Unknown type, but has content field, try to use
                if content:
                    contents.append(
                        {"type": "text", "text": f"[File: {filename}] (Type: {processed_type})\n{content}"}
                    )

        return contents

    def executor_tools_node(self, state: dict) -> dict:
        """
        Executor Tools Node: Use ToolNode to execute tools

        Args:
            state: Current Agent state

        Returns:
            Dictionary containing executor_messages
        """
        if not self.tool_node:
            return {"executor_messages": []}

        # ToolNode requires state dictionary format
        executor_messages = state.get("executor_messages", [])

        try:
            tool_state = {"messages": executor_messages}
            tool_output = self.tool_node.invoke(tool_state)

            # Use state's current_round to keep consistency with executor_agent_node
            task_round = state.get("current_round", 1)

            # Add round metadata to ToolMessage
            result_messages = []
            for msg in tool_output.get("messages", []):
                if isinstance(msg, ToolMessage):
                    msg.metadata = {"round": task_round}
                result_messages.append(msg)

            return {"executor_messages": result_messages}
        except Exception as e:
            # Error handling logic remains unchanged, only return new error message
            last_msg = executor_messages[-1] if executor_messages else None
            if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                # Use state's current_round
                task_round = state.get("current_round", 1)
                error_tool_messages = []
                for tc in last_msg.tool_calls:
                    error_tool_messages.append(
                        ToolMessage(
                            content=f"Tool execution failed: {str(e)}",
                            tool_call_id=tc.get("id", "unknown"),
                            metadata={"round": task_round}
                        )
                    )
                return {"executor_messages": error_tool_messages}
            else:
                return {"executor_messages": [HumanMessage(content=f"Tool execution failed: {str(e)}")]}

    def should_continue(self, state: dict) -> Literal["tools", "final"]:
        """
        Routing function: decide next step based on presence of tool_calls

        Args:
            state: Current Agent state

        Returns:
            "tools" if there are tool calls, otherwise "final"
        """
        executor_messages = state.get("executor_messages", [])
        if not executor_messages:
            return "final"

        last_message = executor_messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "final"

    def executor_final_node(self, state: dict) -> dict:
        """
        Executor Final Node: Integrate results, return final answer

        Args:
            state: Current Agent state

        Returns:
            Dictionary containing execution_results
        """
        todo_list = state.get("todo_list", [])
        current_index = state.get("current_todo_index", 0)

        # If all tasks completed, return final result
        if current_index >= len(todo_list):
            # Get last AI message content as result
            executor_messages = state.get("executor_messages", [])
            final_result = ""
            for msg in reversed(executor_messages):
                if isinstance(msg, AIMessage) and not msg.tool_calls:
                    final_result = msg.content
                    break

            # Use Overwrite to clear message history (bypass reducer)
            return {
                "execution_results": {
                    "status": "completed",
                    "result": final_result
                },
                # Use Overwrite to clear, not return empty list
                "todo_list": Overwrite([]),
                "tool_list": Overwrite([]),
                "executor_messages": Overwrite([])
            }

        # Single task completed, update index and move to next task
        current_todo = todo_list[current_index]
        task_id = current_todo.get("id", "unknown")

        # Get current task result (last AI message)
        executor_messages = state.get("executor_messages", [])
        task_result = ""
        for msg in reversed(executor_messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                task_result = msg.content
                break

        # Create execution results - only keep current task's results in each conversation, do not accumulate previous round's results
        execution_results = [{
            "task_id": task_id,
            "status": "completed",
            "result": task_result
        }]

        # Check if it's the last task
        is_last_task = (current_index + 1) >= len(todo_list)

        # Do not return executor_messages, rely on reducer to automatically maintain complete history
        # Next task will accumulate all context (including previous tasks' conversations and tool execution results)
        # This ensures that multiple tasks in the same todo list can share context
        # executor_messages will be cleared in planner_node (when user confirms new plan, start new round of conversation)
        return {
            "execution_results": {
                "status": "completed" if is_last_task else "in_progress",
                "results": execution_results
            },
            "current_todo_index": current_index + 1
            # No longer return executor_messages, let Reducer maintain existing history
        }

   