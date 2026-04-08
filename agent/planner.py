"""
Planner Agent Module

Responsible for analyzing user intents and generating task plans
"""

from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
import json
import re

from langgraph.types import interrupt

from config.prompts.loader import get_prompt_loader


class AgentPlanner:
    """
    Agent Planner - Responsible for analyzing user intents and generating task plans

    Responsibilities:
    - Analyze user input and pre-processed files
    - Filter tool subsets from global tool library
    - Generate ToDo List and Tool List
    """

    def __init__(self, llm: BaseChatModel, tool_registry=None):
        """
        Initialize Planner

        Args:
            llm: Language model instance
            tool_registry: Tool registry instance
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.prompt_loader = get_prompt_loader()
        self.db = None  # Database instance, will be set externally

    def set_database(self, db):
        """
        Set database instance

        Args:
            db: SessionDatabase instance
        """
        self.db = db

    def plan(self, state: dict) -> dict:
        """
        Generate task plan

        Args:
            state: Current Agent state

        Returns:
            Dictionary containing todo_list, tool_list, planner_messages
        """
        current_round = state.get("current_round", 1)
        messages = self._build_messages(state)

        # Call LLM to generate plan
        response = self.llm.invoke(messages)

        # Add round metadata to response
        response.metadata = {"round": current_round}

        # Parse response
        todo_list, tool_list = self._parse_response(response)

        # Trigger interrupt, wait for user confirmation
        decision = interrupt({
            "type": "plan_approval",
            "todo_list": todo_list,
            "tool_list": tool_list
        })

        # Handle user decision
        if decision.get("action") == "approve":
            return {
                "planner_messages": [response],
                "todo_list": todo_list,
                "tool_list": tool_list
            }
        elif decision.get("action") == "reject":
            # Reject: Add feedback message (round unchanged), trigger re-planning
            feedback = decision.get("reason", "")
            feedback_msg = HumanMessage(
                content=f"User rejected the plan, feedback: {feedback}",
                metadata={"round": current_round}
            )

            # Rebuild messages (including feedback), generate new plan
            revised_messages = messages + [feedback_msg]
            revised_response = self.llm.invoke(revised_messages)
            # Add same round metadata to re-planned response
            revised_response.metadata = {"round": current_round}
            revised_todo_list, revised_tool_list = self._parse_response(revised_response)

            # After re-planning, trigger interrupt again, wait for user confirmation of new plan
            revised_decision = interrupt({
                "type": "plan_approval",
                "todo_list": revised_todo_list,
                "tool_list": revised_tool_list
            })

            # Handle user's decision on re-planning
            if revised_decision.get("action") == "approve":
                # User confirmed new plan, return feedback message and new plan response
                return {
                    "planner_messages": [feedback_msg, revised_response],
                    "todo_list": revised_todo_list,
                    "tool_list": revised_tool_list
                }
            elif revised_decision.get("action") == "reject":
                # User rejected again, return empty list to trigger re-planning
                second_feedback = revised_decision.get("reason", "")
                second_feedback_msg = HumanMessage(
                    content=f"User rejected the plan again, feedback: {second_feedback}",
                    metadata={"round": current_round}
                )
                return {
                    "planner_messages": [feedback_msg, second_feedback_msg],
                    "todo_list": [],  # Empty list triggers routing back to planner
                    "tool_list": []
                }

            # Default return (theoretically should not reach here)
            return {
                "planner_messages": [feedback_msg, revised_response],
                "todo_list": revised_todo_list,
                "tool_list": revised_tool_list
            }

        # Default return (theoretically should not reach here)
        return {
            "planner_messages": [response],
            "todo_list": todo_list,
            "tool_list": tool_list
        }

    def _build_messages(self, state: dict) -> List:
        """
        Build Planner input messages

        Manage context using round field in message metadata:
        - round=0: SystemMessage (always kept)
        - round=1,2,3...: Messages from each round of conversation/task

        Context accumulation strategy:
        1. SystemMessage is added only when round=0
        2. Only keep messages where round <= current_round
        3. HITL rejection scenario: round unchanged, add feedback message to current round
        """
        current_round = state.get("current_round", 1)
        planner_messages = state.get("planner_messages", [])
        session_id = state.get("session_id")

        # 1. SystemMessage is always added (round=0)
        messages = [SystemMessage(content=self._get_system_prompt())]

        # 2. Prepare execution result message (round > 1 and status is completed)
        execution_result_msg = None
        if current_round > 1:
            execution_results = state.get("execution_results", {})
            if execution_results.get("status") == "completed":
                results_summary = self._format_execution_results(execution_results)
                execution_result_msg = HumanMessage(
                    content=f"Previous task execution results:\n{results_summary}",
                    metadata={"round": current_round - 1}
                )

        # 3. Filter messages and insert execution result
        # Execution result should be inserted: after all messages from previous round (round=current_round-1), before messages from current round (round=current_round)
        if execution_result_msg:
            # First add all messages from previous round
            for msg in planner_messages:
                msg_round = (msg.metadata or {}).get("round", 0)
                if msg_round == current_round - 1:
                    messages.append(msg)
            # Then insert execution result
            messages.append(execution_result_msg)
            # Then add messages from current round
            for msg in planner_messages:
                msg_round = (msg.metadata or {}).get("round", 0)
                if msg_round == current_round:
                    messages.append(msg)
        else:
            # No execution result, add using original logic
            for msg in planner_messages:
                msg_round = (msg.metadata or {}).get("round", 0)
                if msg_round <= current_round:
                    messages.append(msg)

        # 4. Add file metadata
        if session_id and self.db:
            file_metadata_list = self.db.get_file_metadata()
            if file_metadata_list:
                metadata_content = self._format_file_metadata(file_metadata_list)
                messages.append(HumanMessage(
                    content=metadata_content,
                    metadata={"round": current_round}
                ))

        return messages

    def _format_file_metadata(self, file_metadata_list: List[dict]) -> str:
        """Format file metadata as Planner prompt"""
        if not file_metadata_list:
            return ""

        file_infos = []
        for meta in file_metadata_list:
            file_infos.append(
                f"- Filename: {meta.get('original_filename', 'unknown')}, "
                f"Type: {meta.get('file_type', 'unknown')}, "
                f"Processed type: {meta.get('processed_type', 'unknown')}"
            )

        template = self.prompt_loader.get_file_content_template()
        return template.format(file_contents="\n".join(file_infos))

    def _convert_dict_to_langchain_message(self, msg_dict: dict) -> Any:
        """Convert dictionary format message to LangChain message"""
        role = msg_dict.get("role", "human")
        content = msg_dict.get("content", "")
        metadata = msg_dict.get("metadata") or {}

        if role == "human":
            return HumanMessage(content=content, metadata=metadata)
        elif role == "ai":
            tool_calls = msg_dict.get("tool_calls", [])
            if isinstance(tool_calls, str):
                import json
                tool_calls = json.loads(tool_calls)
            return AIMessage(content=content, tool_calls=tool_calls, metadata=metadata)
        elif role == "system":
            return SystemMessage(content=content, metadata=metadata)
        elif role == "tool":
            return ToolMessage(
                content=content,
                tool_call_id=msg_dict.get("tool_call_id"),
                metadata=metadata
            )
        return HumanMessage(content=content, metadata=metadata)

    def _convert_to_langchain_message(self, db_msg: dict) -> Any:
        """Convert database message to LangChain message"""
        role = db_msg.get('role', 'human')
        content = db_msg.get('content', '')
        metadata = db_msg.get('metadata') or {}

        if role == 'human':
            return HumanMessage(content=content, metadata=metadata)
        elif role == 'ai':
            tool_calls = json.loads(db_msg.get('tool_calls', '[]')) if db_msg.get('tool_calls') else []
            return AIMessage(content=content, tool_calls=tool_calls, metadata=metadata)
        elif role == 'system':
            return SystemMessage(content=content, metadata=metadata)
        elif role == 'tool':
            return ToolMessage(content=content, tool_call_id=db_msg.get('tool_call_id'), metadata=metadata)

        return HumanMessage(content=content, metadata=metadata)

    def _format_execution_results(self, results: dict) -> str:
        """Format execution_results as readable text"""
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

    def _get_system_prompt(self) -> str:
        """Get system prompt (loaded from YAML configuration)"""
        return self.prompt_loader.get_planner_system_prompt(self._get_tools_description())

    def _get_tools_description(self) -> str:
        """Get tool description"""
        if not self.tool_registry:
            return "No tools available"

        tools = self.tool_registry.list_tools()
        if not tools:
            return "No tools available"

        return "\n".join([f"- {t['name']}: {t['description']}" for t in tools])

    def _parse_response(self, response) -> tuple:
        """
        Parse LLM response, extract todo_list and tool_list

        todo_list format: [{id, description, tool}]
        No longer contains parameters field, parameters are determined by Executor
        """
        content = response.content

        # Try to parse JSON
        try:
            # Extract JSON part
            json_str = self._extract_json(content)

            data = json.loads(json_str)
            todo_list = data.get("todo_list", [])
            tool_names = data.get("tool_list", [])

            # Get tool descriptions by tool names
            tool_list = self._get_tool_descriptions(tool_names)

            # Ensure each task in todo_list only contains {id, description, tool}
            # Remove parameters field if it exists
            cleaned_todo_list = []
            for todo in todo_list:
                cleaned_todo = {
                    "id": todo.get("id", ""),
                    "description": todo.get("description", ""),
                    "tool": todo.get("tool", "")
                }
                cleaned_todo_list.append(cleaned_todo)

            return cleaned_todo_list, tool_list

        except (json.JSONDecodeError, Exception) as e:
            # Parse failed, return empty list
            print(f"Failed to parse Planner response: {e}")
            return [], []

    def _extract_json(self, content: str) -> str:
        """Extract JSON string from response"""
        # Try to extract ```json block
        if "```json" in content:
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                return match.group(1).strip()

        # Try to extract ``` block
        if "```" in content:
            match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                return match.group(1).strip()

        # Try to find first { and last }
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            return content[start:end]

        return content

    def _get_tool_descriptions(self, tool_names: List[str]) -> List[dict]:
        """Get tool descriptions based on tool names"""
        if not self.tool_registry:
            return []

        result = []
        for name in tool_names:
            tool = self.tool_registry.get_tool(name)
            if tool:
                result.append({
                    "name": name,
                    "description": tool.description
                })

        return result
