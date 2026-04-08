"""
Prompt Loader Module

Responsible for loading and managing prompt configurations from YAML files
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class PromptLoader:
    """
    Prompt Loader

    Load prompt configurations from YAML files, support template rendering
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize prompt loader

        Args:
            config_dir: Configuration directory, defaults to project's config/prompts directory
        """
        if config_dir is None:
            # Default to project's config/prompts directory
            self.config_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.config_dir = Path(config_dir)

        self._planner_prompts: Optional[Dict[str, Any]] = None
        self._executor_prompts: Optional[Dict[str, Any]] = None

    def load_planner_prompts(self) -> Dict[str, Any]:
        """
        Load Planner prompts

        Returns:
            Planner prompts dictionary
        """
        if self._planner_prompts is not None:
            return self._planner_prompts

        prompt_file = self.config_dir / "planner.yaml"

        if not prompt_file.exists():
            return self._get_default_planner_prompts()

        with open(prompt_file, "r", encoding="utf-8") as f:
            self._planner_prompts = yaml.safe_load(f)

        return self._planner_prompts

    def load_executor_prompts(self) -> Dict[str, Any]:
        """
        Load Executor prompts

        Returns:
            Executor prompts dictionary
        """
        if self._executor_prompts is not None:
            return self._executor_prompts

        prompt_file = self.config_dir / "executor.yaml"

        if not prompt_file.exists():
            return self._get_default_executor_prompts()

        with open(prompt_file, "r", encoding="utf-8") as f:
            self._executor_prompts = yaml.safe_load(f)

        return self._executor_prompts

    def get_planner_system_prompt(self, tools_description: str) -> str:
        """
        Get Planner system prompt

        Args:
            tools_description: Tool description string

        Returns:
            Formatted system prompt
        """
        prompts = self.load_planner_prompts()
        template = prompts.get("system_prompt", self._get_default_planner_prompts()["system_prompt"])
        # Use replace() instead of format() to avoid misinterpreting {id, description, tool} in template
        return template.replace("{tools}", tools_description)

    def get_replan_feedback_prompt(self, feedback: str) -> str:
        """
        Get re-planning feedback prompt

        Args:
            feedback: User feedback

        Returns:
            Formatted feedback prompt
        """
        prompts = self.load_planner_prompts()
        template = prompts.get("replan_feedback_prompt", "{feedback}")
        return template.format(feedback=feedback)

    def get_file_content_template(self) -> str:
        """
        Get file content template

        Returns:
            File content template string
        """
        prompts = self.load_planner_prompts()
        return prompts.get("file_content_template", "## Input File Content\n\n{file_contents}")

    def get_text_file_template(self) -> str:
        """
        Get text file template

        Returns:
            Text file template string
        """
        prompts = self.load_planner_prompts()
        return prompts.get("text_file_template", "### File: {filename}\n{content}")

    def get_image_file_template(self) -> str:
        """
        Get image file template

        Returns:
            Image file template string
        """
        prompts = self.load_planner_prompts()
        return prompts.get("image_file_template", "### Image: {filename}\n[Image file uploaded]")

    def get_execution_system_prompt(
        self,
        max_retries: int = 3,
        file_contents: str = "",
        tool_descriptions: str = ""
    ) -> str:
        """
        Get Executor system prompt

        Args:
            max_retries: Maximum retry count
            file_contents: File content string
            tool_descriptions: Tool description string

        Returns:
            Formatted system prompt
        """
        prompts = self.load_executor_prompts()
        template = prompts.get("execution_system_prompt", "")

        # If tool descriptions not provided, try to get from registry (if available)
        if not tool_descriptions:
            tool_descriptions = self._get_tool_descriptions()

        return template.format(
            tool_descriptions=tool_descriptions or "No tools available",
            file_contents=file_contents or "No file content available",
            max_retries=max_retries
        )

    def get_task_instruction_template(self) -> str:
        """
        Get task instruction template

        Returns:
            Task instruction template string
        """
        prompts = self.load_executor_prompts()
        return prompts.get("task_instruction_template", "Execute task: {task_description}")

    def _get_tool_descriptions(self) -> str:
        """Get tool descriptions (internal method)"""
        # This method tries to get tool descriptions from tool_registry
        # If no registry is available, return empty string
        try:
            from tools.registry import ToolRegistry
            # Cannot directly get registry instance here, return empty string
            # In actual usage, it needs to be passed by the caller
            return ""
        except ImportError:
            return ""

    def get_retry_prompt(self, error_message: str, attempt: int, max_retries: int) -> str:
        """
        Get retry prompt

        Args:
            error_message: Error message
            attempt: Current attempt count
            max_retries: Maximum retry count

        Returns:
            Retry prompt string
        """
        prompts = self.load_executor_prompts()
        template = prompts.get("retry_prompt", "Execution error: {error_message}")
        return template.format(error_message=error_message, attempt=attempt, max_retries=max_retries)

    def _get_default_planner_prompts(self) -> Dict[str, Any]:
        """Get default Planner prompts"""
        return {
            "system_prompt": """You are an intelligent task planning assistant (Agent Planner).

Your responsibilities:
1. Analyze user requests and input files
2. Select appropriate tools from available tools
3. Generate a detailed task list (ToDo List)

Important rules:
[Tool Selection Principles]
- Only assign tools for tasks that actually require tool operations
- For pure thinking tasks like analysis, comparison, summarization, if no specific tool is needed, set the tool field to null or empty string ""
- Do not forcibly assign tools to every task just to "complete the task"

[Tool Restrictions]
- Only select tools from the "Available Tools" list below
- Absolutely do not fabricate tools that do not exist in the list

[Task Decomposition]
- Ensure clear logical order between tasks
- Select only necessary tools
- Task descriptions should be clear and specific

Output format:
Please return in JSON format, containing two fields:
- todo_list: Task list, each task contains {{id, description, tool}}
  - id: Task unique identifier (string)
  - description: Task description
  - tool: Tool name to use (only specify tool name, parameters are determined by Executor; null or "" when no tool is needed)
- tool_list: List of tool names to use (string array)

Available tools:
{tools}

Please strictly follow the JSON format output, do not include other content.""",
            "replan_feedback_prompt": """User rejected the previous plan, feedback as follows:
{feedback}

Please regenerate the plan based on user feedback.""",
            "file_content_template": "## Input File Content\n\n{file_contents}",
            "text_file_template": "### File: {filename}\n{content}",
            "image_file_template": "### Image: {filename}\n[Image file uploaded]"
        }

    def _get_default_executor_prompts(self) -> Dict[str, Any]:
        """Get default Executor prompts"""
        return {
            "execution_system_prompt": """You are a task execution assistant (Agent Executor).

Your responsibilities:
1. Execute specific operations based on given task descriptions
2. Correctly use tools to complete tasks
3. Return clear execution results

Execution flow:
1. Analyze task requirements and parameters
2. Select appropriate tools
3. Call tools and get results
4. If tool call fails, analyze error reason and retry
5. Return final execution result

Notes:
1. Strictly follow task requirements
2. When tool call fails, retry at most {max_retries} times
3. Return results should be clear and accurate""",
            "task_instruction_template": "Execute task: {task_description}",
            "retry_prompt": "Execution error: {error_message}\nThis is attempt {attempt} of {max_retries}\nPlease adjust method and retry."
        }

    def reload_all(self):
        """Reload all prompts"""
        self._planner_prompts = None
        self._executor_prompts = None
        self.load_planner_prompts()
        self.load_executor_prompts()


# Global prompt loader instance
_global_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get global prompt loader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = PromptLoader()
    return _global_loader


def load_planner_prompts() -> Dict[str, Any]:
    """Load Planner prompts"""
    return get_prompt_loader().load_planner_prompts()


def load_executor_prompts() -> Dict[str, Any]:
    """Load Executor prompts"""
    return get_prompt_loader().load_executor_prompts()
