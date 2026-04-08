"""
Web Search Tool Module

Use Tavily search engine for web searches
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_tavily import TavilySearch


def _load_config() -> dict:
    """Load tools/config.yaml configuration file"""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def _get_tavily_api_key() -> str:
    """
    Get Tavily API Key

    Priority:
    1. Configuration in config.yaml
    2. Environment variable TAVILY_API_KEY
    """
    config = _load_config()

    # Prefer reading from config.yaml
    api_key = config.get("web_search", {}).get("tavily_api_key", "")

    # If not in config, read from environment variable
    if not api_key:
        api_key = os.getenv("TAVILY_API_KEY", "")

    return api_key

# =============================================================================
# DuckDuckGo Implementation (commented out, kept for reference)
# =============================================================================
# from langchain_community.tools import DuckDuckGoSearchResults
#
#
# class WebSearchQuery(BaseModel):
#     """Web search query parameters"""
#     query: str = Field(description="Search query keyword")
#     num_results: int = Field(default=5, description="Number of results to return, default 5")
#
#
# @tool(args_schema=WebSearchQuery)
# def web_search_duckduckgo(query: str, num_results: int = 5) -> str:
#     """
#     Web search tool. Use DuckDuckGo search engine to search for information on the internet.
#
#     Args:
#         query: Search query keyword
#         num_results: Number of results to return, default 5
#
#     Returns:
#         Formatted web search results (including title and snippet)
#     """
#     print(f"[WebSearch] Search request received: {query} (num_results={num_results})")
#
#     # Initialize DuckDuckGo search tool
#     search_tool = DuckDuckGoSearchResults(
#         max_results=num_results,
#         output_format="list"  # Return list format
#     )
#
#     try:
#         # Execute search
#         results = search_tool.run(query)
#         print(f"[WebSearch] Search completed, returning {len(results)} results")
#     except Exception as e:
#         print(f"[WebSearch] Search failed: {str(e)}")
#         return f"Search failed: {str(e)}"
#
#     # Process search results
#     # results format may be string or list
#     if isinstance(results, str):
#         return results
#
#     # results format: [{'snippet': 'snippet', 'title': 'title', 'link': 'url'}, ...]
#     formatted_results = []
#     for i, result in enumerate(results, 1):
#         if isinstance(result, dict):
#             title = result.get('title', 'No title')
#             snippet = result.get('snippet', 'No snippet')
#             link = result.get('link', '')
#
#             formatted_results.append(
#                 f"{i}. **{title}**\n"
#                 f"   {snippet}\n"
#                 f"   URL: {link}"
#             )
#         else:
#             # If result is not a dict, add directly
#             formatted_results.append(f"{i}. {str(result)}")
#
#     if not formatted_results:
#         return "No relevant search results found"
#
#     return "\n\n".join(formatted_results)
# =============================================================================


class WebSearchQuery(BaseModel):
    """Web search query parameters"""
    query: str = Field(description="Search query keyword")
    num_results: int = Field(default=5, description="Number of results to return, default 5")


@tool(args_schema=WebSearchQuery)
def web_search(query: str, num_results: int = 5) -> str:
    """
    Web search tool. Use Tavily search engine to search for information on the internet.

    Args:
        query: Search query keyword
        num_results: Number of results to return, default 5

    Returns:
        Formatted web search results (including title and snippet)
    """
    print(f"[WebSearch] Search request received: {query} (num_results={num_results})")

    # Get API Key (from config.yaml or environment variable)
    api_key = _get_tavily_api_key()
    if not api_key:
        print("[WebSearch] Error: TAVILY_API_KEY not configured, please set in config.yaml or environment variable")
        return "Error: TAVILY_API_KEY not configured, please set in tools/config.yaml or environment variable"

    # Initialize Tavily search tool
    search_tool = TavilySearch(
        max_results=num_results,
        api_key=api_key,
    )

    try:
        # Execute search
        results = search_tool.run(query)
        print(f"[WebSearch] Search completed, returning {len(results) if results else 0} results")
    except Exception as e:
        print(f"[WebSearch] Search failed: {str(e)}")
        return f"Search failed: {str(e)}"

    # Process search results
    # Tavily response format: [{'title': 'title', 'content': 'snippet', 'url': 'url', 'score': score}, ...]
    if isinstance(results, str):
        return results

    if not results:
        return "No relevant search results found"

    formatted_results = []
    for i, result in enumerate(results, 1):
        if isinstance(result, dict):
            title = result.get('title', 'No title')
            snippet = result.get('content', result.get('snippet', 'No snippet'))
            link = result.get('url', result.get('link', ''))

            formatted_results.append(
                f"{i}. **{title}**\n"
                f"   {snippet}\n"
                f"   URL: {link}"
            )
        else:
            # If result is not a dict, add directly
            formatted_results.append(f"{i}. {str(result)}")

    return "\n\n".join(formatted_results)


def build_web_search_tool():
    """Build web search tool"""
    return web_search
