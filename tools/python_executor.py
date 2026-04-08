"""
Python Code Execution Tool Module

Python code execution tool (non-plotting). For executing Python code for data processing, calculations, text analysis and other logical operations.
"""

from langchain_core.tools import tool


@tool
def execute_python_code(code: str, timeout: int = 30) -> str:
    """
    Execute Python code

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds, default 30 seconds

    Returns:
        Code execution result
    """
    # Temporary implementation - return mock result
    # Note: Actual implementation should use a secure sandbox environment
    return f"Code execution result: Code executed (temporary implementation)\nOutput: [result]"


@tool
def evaluate_expression(expression: str) -> str:
    """
    Evaluate mathematical expression

    Args:
        expression: Mathematical expression string

    Returns:
        Calculation result
    """
    # Temporary implementation - return mock result
    try:
        # Simple safe calculation example
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Calculation result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


@tool
def process_text(text: str, operation: str) -> str:
    """
    Text processing operation

    Args:
        text: Input text
        operation: Operation type ("uppercase", "lowercase", "reverse", "word_count")

    Returns:
        Processing result
    """
    # Temporary implementation
    operations = {
        "uppercase": lambda t: t.upper(),
        "lowercase": lambda t: t.lower(),
        "reverse": lambda t: t[::-1],
        "word_count": lambda t: f"Word count: {len(t.split())}"
    }

    if operation in operations:
        result = operations[operation](text)
        return f"Text processing result: {result}"
    return f"Unknown operation: {operation}"


def build_python_executor_tool():
    """Build Python execution tool"""
    return execute_python_code
