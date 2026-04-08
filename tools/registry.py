"""
Tool Registry Module
"""

from typing import List, Dict, Any, Optional


class ToolRegistry:
    """Tool registry"""

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def register(self, tool, category: str = None, tags: List[str] = None, description_override: str = None):
        """Register a tool"""
        name = getattr(tool, 'name', str(tool))
        self._tools[name] = {
            'tool': tool,
            'category': category,
            'tags': tags or [],
            'description': description_override or getattr(tool, 'description', '')
        }

    def get_tool(self, name: str) -> Optional[Any]:
        """Get tool instance"""
        if name in self._tools:
            return self._tools[name]['tool']
        return None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools"""
        return [
            {
                'name': name,
                'description': info['description'],
                'category': info['category'],
                'tags': info['tags']
            }
            for name, info in self._tools.items()
        ]
